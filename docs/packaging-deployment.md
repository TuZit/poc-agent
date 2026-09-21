# Đóng gói (Packaging) & Triển khai (Deployment)

**Sản phẩm:** Agent Kit POC (`agent-kit`) · **Phiên bản:** 0.1.0
**Đối tượng:** dev/DevOps phát hành và triển khai bộ kit.

> Tài liệu này mô tả **cách đóng gói artifact** và **cách triển khai** POC ra môi
> trường thật (máy dev, CI/CD, container). Toàn bộ lệnh đã được chạy kiểm chứng
> trên macOS + Python 3.12, trừ phần Docker (xem ghi chú ở mục 8).

---

## 1. Tổng quan artifact

| Artifact | Tạo bằng | Dùng cho |
|---|---|---|
| **Wheel** `dist/agent_kit_poc-<ver>-py3-none-any.whl` | `uv build` | Kênh phân phối chính — cài bằng `uv tool` / `pipx` / `pip` |
| **Sdist** `dist/agent_kit_poc-<ver>.tar.gz` | `uv build` | Build lại từ source (audit, rebuild nội bộ) |
| **Docker image** `agent-kit-poc` | `docker build` | Chạy trong container, CI, môi trường cô lập |
| **Bundle asset** (`skills/`, `templates/`, `samples/`, `integrations/`) | tự động | Được nhúng **bên trong wheel** — không phát hành rời |
| **Lock file** `uv.lock` | `uv lock` | Tái lập chính xác cây dependency |

Điểm quan trọng: **wheel là self-contained**. Skill, template project, sample và
template Kiro đều nằm trong wheel, nên `agent-kit` cài xong là dùng được ngay,
không cần source checkout.

---

## 2. Cấu trúc package

```text
dsh-build/
├── pyproject.toml            # metadata + build backend (hatchling)
├── uv.lock                   # dependency đã ghim
├── src/
│   └── agent_kit/            # package duy nhất được cài
│       ├── cli/ agent/ model/ tools/ skills/
│       ├── workflow/ evaluation/ config/ mcp/ integrations/
│       ├── paths.py          # resolve asset bundled vs source
│       └── scaffold.py       # render template
├── skills/ templates/ samples/ integrations/   # asset ở repo root → force-include vào wheel
├── tests/                    # KHÔNG nằm trong wheel
└── docs/ specs/ .specify/    # KHÔNG nằm trong wheel
```

Layout `src/` ngăn việc import nhầm package chưa cài; `tests/`, `docs/`, `specs/`
không được đóng gói nên image/wheel gọn.

### `pyproject.toml` — các phần quyết định đóng gói

```toml
[project]
name = "agent-kit-poc"
dynamic = ["version"]                 # version lấy từ agent_kit.__version__
requires-python = ">=3.11"
dependencies = ["typer>=0.12", "pyyaml>=6.0"]     # runtime tối thiểu

[project.optional-dependencies]
openai = ["openai>=1.40"]             # SDK provider nằm ở extra, không bắt buộc

[project.scripts]
agent-kit = "agent_kit.cli.main:app"  # entry point sinh ra binary `agent-kit`

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "src/agent_kit/__init__.py"    # một nguồn version duy nhất

[tool.hatch.build.targets.wheel]
packages = ["src/agent_kit"]

[tool.hatch.build.targets.wheel.force-include]     # asset → package data
"skills" = "agent_kit/_bundled/skills"
"templates" = "agent_kit/_bundled/templates"
"samples" = "agent_kit/_bundled/samples"
"integrations" = "agent_kit/_bundled/integrations"
```

| Nhóm dependency | Nội dung | Ai cần |
|---|---|---|
| `dependencies` | `typer`, `pyyaml` | mọi bản cài |
| `optional-dependencies[openai]` | `openai` | chỉ khi dùng `model.provider: openai` |
| `dependency-groups.dev` | `pytest`, `ruff` | dev/CI (không vào wheel) |

---

## 3. Đóng gói asset — điểm dễ vỡ nhất

Asset nằm ở **repo root** lúc phát triển nhưng phải nằm **trong package** khi cài.
Cầu nối là `force-include` + `src/agent_kit/paths.py`:

```python
def asset_dir(name: str) -> Path:
    bundled = package_root() / "_bundled" / name     # 1) bản đã cài (wheel)
    if bundled.is_dir():
        return bundled
    dev = repo_root_candidate() / name               # 2) fallback source checkout
    if dev.is_dir():
        return dev
    raise AssetError(...)                            # 3) báo lỗi kèm lệnh cài lại
```

Nhờ vậy `uv run agent-kit` (editable, dùng source) và `agent-kit` (đã cài, dùng
`_bundled`) hành xử giống nhau.

### Kiểm chứng asset có trong wheel

```bash
cd dsh-build
uv build
python3 - <<'PY'
import glob, zipfile
whl = glob.glob("dist/*.whl")[0]
names = zipfile.ZipFile(whl).namelist()
for p in ("skills", "templates", "samples", "integrations"):
    prefix = f"agent_kit/_bundled/{p}"
    print(prefix, len([n for n in names if n.startswith(prefix)]), "file(s)")
print("tổng file trong wheel:", len(names))
PY
```

Kết quả thực tế của bản 0.1.0:

```text
agent_kit/_bundled/skills 2 file(s)
agent_kit/_bundled/templates 2 file(s)
agent_kit/_bundled/samples 2 file(s)
agent_kit/_bundled/integrations 12 file(s)
tổng file trong wheel: 61
```

Kiểm chứng lúc runtime rằng asset đang lấy từ bản **đã cài** (không phải source):

```bash
~/.local/share/uv/tools/agent-kit-poc/bin/python -c \
  "from agent_kit.paths import skills_dir; print(skills_dir())"
# .../site-packages/agent_kit/_bundled/skills
```

> ⚠️ **Nếu thêm thư mục asset mới**, phải: (1) thêm vào `force-include`,
> (2) thêm tên vào `ASSET_NAMES` trong `paths.py`, (3) thêm vào
> `[tool.hatch.build.targets.sdist] include`. Bỏ sót bước nào thì `pytest` vẫn
> xanh nhưng bản cài sẽ thiếu file — hãy chạy mục 6 để chắc chắn.

---

## 4. Version một nguồn

Version chỉ nằm ở `src/agent_kit/__init__.py`:

```python
__version__ = "0.1.0"
```

Hatchling đọc giá trị này (`[tool.hatch.version]`) để đặt tên artifact và metadata.
**Phát hành bản mới = sửa đúng một dòng**, sau đó:

```bash
uv run python -c "import agent_kit, importlib.metadata as m; print(agent_kit.__version__, m.version('agent-kit-poc'))"
# 0.1.0 0.1.0   ← hai giá trị phải trùng nhau
```

Quy ước (semver): `PATCH` sửa lỗi/nội dung skill, `MINOR` thêm tool/model/workflow,
`MAJOR` đổi format `config.yaml` hoặc interface.

---

## 5. Build & lock

```bash
cd dsh-build
uv lock                 # ghim dependency, cập nhật uv.lock (commit file này)
uv lock --check         # CI: xác nhận lock còn khớp pyproject
uv build                # sinh cả wheel + sdist vào dist/
uv build --wheel        # chỉ wheel
uv build --sdist        # chỉ sdist
rm -rf dist             # dọn trước khi build lại
```

`dist/` đã nằm trong `.gitignore` — **không commit artifact**, chỉ commit
`pyproject.toml` + `uv.lock` + source. Artifact nên được upload lên nơi lưu trữ
(CI artifact, internal package index, release).

Cài lại môi trường dev đúng theo lock:

```bash
uv sync --frozen --all-extras     # --frozen: từ chối cập nhật lock
```

---

## 6. Kiểm tra artifact trước khi phát hành

Nguyên tắc: **test trên wheel đã cài, không test trên source checkout.**

```bash
cd dsh-build
rm -rf dist && uv build

# 1) cài từ wheel vào môi trường sạch (không dùng source)
uv tool install dist/agent_kit_poc-0.1.0-py3-none-any.whl --force
agent-kit --version

# 2) chạy demo hoàn toàn ngoài repo, chỉ có CLI đã cài
rm -rf /tmp/release-check && mkdir -p /tmp/release-check && cd /tmp/release-check
agent-kit init release-project --ai kiro
cd release-project
agent-kit config set model.provider mock
agent-kit doctor                                    # → Agent environment is ready.
agent-kit run                                       # → output/sample-001.md
agent-kit evaluate output/sample-001.md             # → Result: PASS
agent-kit kiro status                               # → Kiro integration is complete.
```

Đây là bước bắt được lỗi thiếu asset — thứ mà `pytest` không phát hiện được.

### Checklist trước khi phát hành

| ☐ | Việc | Lệnh |
|---|---|---|
| ☐ | Test xanh, offline | `uv run pytest` (166 passed) |
| ☐ | Lint sạch | `uv run ruff check src tests` |
| ☐ | Lock còn khớp | `uv lock --check` |
| ☐ | Version đã bump + khớp metadata | mục 4 |
| ☐ | Wheel chứa đủ asset | mục 3 |
| ☐ | Cài từ wheel chạy được demo | mục 6 |
| ☐ | Docker image build + chạy được | mục 8 |
| ☐ | Docs cập nhật (`README`, `docs/*`, `.kiro/specs`, `specs/`) | — |
| ☐ | Commit sạch, đã tag version | `git tag v0.1.0` |

---

## 7. Các cách phân phối

| Cách | Lệnh | Khi nào dùng |
|---|---|---|
| **uv tool** (khuyến nghị) | `uv tool install '.[openai]' --force` hoặc `uv tool install dist/*.whl --force` | máy dev/tester |
| **uv tool từ git** | `uv tool install "git+https://host/repo.git@v0.1.0"` | chưa có package index |
| **pipx** | `pipx install 'agent-kit-poc[openai]'` | đã dùng pipx cho CLI khác |
| **pip trong venv** | `python -m venv .venv && .venv/bin/pip install 'agent-kit-poc[openai]'` | nhúng vào app Python khác |
| **Nội bộ / air-gapped** | `pip install --no-index --find-links=/kho/wheels 'agent-kit-poc[openai]'` | máy không ra internet |
| **Docker** | `docker build -t agent-kit-poc .` | CI, môi trường cô lập |

Cài không có extras (chỉ dùng `model.provider: mock`) giúp giảm dependency và
không cần mạng:

```bash
uv tool install dist/agent_kit_poc-0.1.0-py3-none-any.whl --force
```

---

## 8. Triển khai bằng Docker

`Dockerfile` (đã có trong repo):

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY skills ./skills
COPY templates ./templates
COPY samples ./samples
COPY integrations ./integrations
RUN uv sync --frozen --no-dev --all-extras      # cài đúng theo lock
RUN useradd --create-home --uid 10001 agent \
    && mkdir -p /work && chown -R agent:agent /work /app
USER agent                                     # KHÔNG chạy bằng root
WORKDIR /work
CMD ["agent-kit", "--help"]
```

Đặc tính triển khai:

| Đặc tính | Cách đảm bảo |
|---|---|
| Tái lập được | `uv sync --frozen` + `python:3.12-slim` |
| Không nhúng secret | không có `ENV OPENAI_API_KEY`; key truyền lúc `docker run` |
| Không chạy root | `USER agent` (uid 10001) |
| Có thư mục làm việc ghi được | `/work` được `chown` cho user `agent` |
| Kích thước gọn | `.dockerignore` loại `.venv`, `tests/`, `docs/`, `specs/`, `dist/` |

### Lệnh vận hành

```bash
docker build -t agent-kit-poc:0.1.0 .

# kiểm tra nhanh
docker run --rm agent-kit-poc:0.1.0 agent-kit --version
docker run --rm agent-kit-poc:0.1.0 agent-kit doctor          # trong /work
docker run --rm agent-kit-poc:0.1.0 agent-kit mcp tools

# chạy trên project của bạn (mount + secret qua env)
docker run --rm -v "$PWD:/work" -e OPENAI_API_KEY agent-kit-poc:0.1.0 \
  agent-kit run --project /work

# dùng file env thay vì gõ key trên command line
docker run --rm -v "$PWD:/work" --env-file .env agent-kit-poc:0.1.0 \
  agent-kit doctor --project /work

# chế độ offline, không cần secret
docker run --rm -v "$PWD:/work" agent-kit-poc:0.1.0 \
  agent-kit run --project /work          # khi config đã đặt provider: mock

# smoke test trong container (chạy init ngay trong /work)
docker run --rm agent-kit-poc:0.1.0 sh -lc \
  'agent-kit init demo && agent-kit config set model.provider mock --project demo \
   && agent-kit run --project demo && agent-kit evaluate demo/output/sample-001.md'
```

> ⚠️ **Trạng thái kiểm chứng:** máy build POC này **không có Docker**, nên
> `Dockerfile` mới chỉ được review tĩnh, chưa build thật. Trước khi dùng chính
> thức, chạy mục 6 của checklist (build image + smoke test ở trên) và ghi lại kết
> quả. Nếu base image `python:3.12-slim` không pull được, dùng mirror nội bộ và
> thay dòng `COPY --from=ghcr.io/astral-sh/uv:latest` bằng cách `pip install uv`.

---

## 9. Triển khai trong CI/CD

Ví dụ GitHub Actions chạy **không cần secret** (dùng `mock`) và lưu output làm
artifact:

```yaml
name: agent-kit

on:
  push:
    branches: [main]
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true }

      - name: Sync (đúng theo lock)
        run: uv sync --frozen --all-extras

      - name: Lint
        run: uv run ruff check src tests

      - name: Test (offline, không cần OPENAI_API_KEY)
        run: uv run pytest

      - name: Build artifact
        run: uv build

      - name: Kiểm tra wheel tự chứa asset
        run: |
          uv tool install dist/*.whl --force
          uv run agent-kit init demo-project
          uv run agent-kit config set model.provider mock --project demo-project
          uv run agent-kit doctor --project demo-project
          uv run agent-kit run --project demo-project
          uv run agent-kit evaluate demo-project/output/sample-001.md

      - uses: actions/upload-artifact@v4
        with:
          name: distribution
          path: dist/
```

Ghi chú CI:

- `--project <dir>` cho phép chạy mọi lệnh từ repo root mà không cần `cd`.
- Job trên chạy hoàn toàn với `mock`: nhanh, tất định, không tốn phí model.
- Muốn chạy model thật theo lịch (nightly), thêm job riêng và truyền secret:
  `env: { OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }} }` rồi
  `agent-kit config set model.provider openai --project demo-project`.
- **Never** đặt `OPENAI_API_KEY` trong file cấu hình được commit.

---

## 10. Cấu hình theo môi trường & quản lý secret

### Biến môi trường

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | khi `provider: openai` | khoá API; `doctor` kiểm tra và báo nếu thiếu |
| `OPENAI_BASE_URL` | không | đổi endpoint (Azure/proxy/gateway nội bộ) |
| `AGENT_KIT_MODEL` | không | tên model dùng khi `.agent/config.yaml` **không** khai báo `model.name` |
| `PATH` | — | phải chứa `~/.local/bin` (uv tool) để Kiro/hook gọi được `agent-kit` |

`AGENT_KIT_MODEL` cho phép **cùng một image/wheel chạy nhiều môi trường** mà không
phải sửa YAML:

```bash
AGENT_KIT_MODEL=gpt-4o-mini agent-kit doctor --project ./demo   # Model configuration (openai/gpt-4o-mini)
```

Nếu thiếu cả YAML lẫn biến này, lệnh sẽ báo:

```text
✗ model.name is required in .../.agent/config.yaml (e.g. 'gpt-4o-mini').
  It can also be provided through the AGENT_KIT_MODEL environment variable.
```

### Nguyên tắc cấu hình

| Loại cấu hình | Đặt ở đâu | Commit? |
|---|---|---|
| Hành vi agent (model provider, tools, skills, workflow) | `.agent/config.yaml` | ✅ commit được |
| Tên model theo môi trường | `AGENT_KIT_MODEL` | ❌ theo môi trường |
| Secret | biến môi trường / secret manager / `--env-file` | ❌ tuyệt đối không |
| Cấu hình Kiro | `.kiro/*` | ✅ commit được |

Ví dụ tách môi trường bằng env:

```bash
# dev: offline, miễn phí
agent-kit config set model.provider mock

# staging/prod: cùng file config, chỉ khác env
export OPENAI_API_KEY=...        # từ secret manager / GitHub Secrets / .env không commit
export AGENT_KIT_MODEL=gpt-4o-mini
agent-kit doctor && agent-kit run
```

`.gitignore` đã chặn `.env`, `.env.local`, `*.local.env`, `output/` — secret và
kết quả chạy không bị commit nhầm.

> ⚠️ **Sửa YAML cẩn thận:** mọi key lạ dưới `model:` được chuyển tiếp thành
> `options` cho provider (theo thiết kế). Nếu bạn thụt lề sai khiến `tools:` nằm
> trong `model:`, tool sẽ bị **tắt âm thầm**. Luôn kiểm chứng bằng
> `agent-kit doctor` (dòng `✓ Tools (...)`) hoặc dòng đầu của `agent-kit run`
> (`tools=filesystem, shell`). Nếu thấy `tools=(none)`, hãy chạy
> `agent-kit config show` để xem cấu trúc thật.

---

## 11. Nâng cấp, rollback, gỡ cài

```bash
# nâng cấp từ wheel mới
uv tool install dist/agent_kit_poc-0.2.0-py3-none-any.whl --force
agent-kit --version

# rollback: cài lại wheel cũ (giữ artifact của mọi bản phát hành!)
uv tool install dist/agent_kit_poc-0.1.0-py3-none-any.whl --force

# gỡ hoàn toàn
uv tool uninstall agent-kit-poc

# gỡ lớp tích hợp Kiro trong một project (không xoá file của bạn)
agent-kit kiro uninstall --yes --project ./demo
```

Nâng cấp **không** tự đổi `.agent/config.yaml` hay `.kiro/*` của project đang
dùng: hai lệnh `agent-kit kiro install` và `agent-kit init` chỉ ghi đè khi có
`--force`. Vì vậy khi template thay đổi, xem diff:

```bash
agent-kit kiro install --force --project ./demo && git -C demo diff
```

Khuyến nghị: giữ `dist/` của mọi bản đã phát hành (CI artifact hoặc internal
index) để rollback trong 1 lệnh.

---

## 12. Vận hành & quan sát (trong phạm vi POC)

### Exit code — dùng để gate trong CI/script

| Lệnh | 0 | 1 |
|---|---|---|
| `agent-kit doctor` | môi trường sẵn sàng | thiếu config / thiếu key / sai workflow |
| `agent-kit run` | chạy xong, output hợp lệ | input không tồn tại, lỗi model, output thiếu section |
| `agent-kit evaluate` | `Result: PASS` | `Result: FAIL` hoặc file không tồn tại |
| `agent-kit kiro status` | đủ file tích hợp | còn file thiếu |
| `agent-kit mcp call` | tool chạy thành công | lỗi tham số/tool (`isError: true`) |

### Kênh output

| Kênh | Nội dung |
|---|---|
| **stdout** | kết quả người đọc: báo cáo `doctor`, nội dung `evaluate`, kết quả MCP tool |
| **stderr** | lỗi có tiền tố `✗` + hướng dẫn; với `mcp serve` là dòng chẩn đoán khởi động |
| **stdout của `mcp serve`** | **chỉ** JSON-RPC — không được trộn log vào đây |

Ví dụ gate trong pipeline:

```bash
set -euo pipefail
agent-kit doctor              || exit 1
agent-kit run                 || exit 1
agent-kit evaluate output/sample-001.md   # FAIL sẽ trả exit 1 và chặn deploy
```

Ghi log khi chạy nền:

```bash
agent-kit run > run.log 2>&1 || echo "agent-kit run thất bại, xem run.log"
```

**Chưa có trong POC:** log file, metrics, tracing, health endpoint, retry/backoff.
Đây là phần nằm ngoài phạm vi (xem mục 13).

---

## 13. Giới hạn khi lên production

POC **chưa sẵn sàng cho production**. Các khoảng trống cần xử lý trước khi triển
khai thật:

| # | Giới hạn hiện tại | Việc cần làm trước production |
|---|---|---|
| 1 | Không có xác thực/phân quyền cho MCP server | Chỉ chạy MCP cục bộ trong IDE; nếu mở ra mạng phải thêm auth + TLS |
| 2 | Sandbox tool chỉ ở mức POC (whitelist lệnh, giới hạn path) | Chạy trong container/VM riêng, thêm seccomp/AppArmor, user không quyền |
| 3 | Một provider thật duy nhất (`openai`) | Thêm provider/fallback nếu cần đa nhà cung cấp |
| 4 | Không rate limit, không retry, không timeout phía model | Thêm giới hạn chi phí, retry có backoff, timeout theo yêu cầu |
| 5 | Secret là biến môi trường dạng plain | Dùng secret manager (Vault/SSM/Secrets Manager), xoay khoá định kỳ |
| 6 | Không có metrics/tracing | Thêm export (OpenTelemetry) + dashboard chi phí/latency |
| 7 | Một tiến trình, một project | Thiết kế multi-tenant, hàng đợi, cô lập theo project |
| 8 | `config set` ghi lại YAML và **mất comment** | Với production, quản lý config bằng template/IaC thay vì sửa tay |
| 9 | Chưa kiểm thử tải/đồng thời | Load test trước khi mở cho nhiều người dùng |

---

## 14. Checklist triển khai

| ☐ | Bước | Lệnh / tiêu chí |
|---|---|---|
| ☐ | Chốt version & bump | sửa `__version__`, `uv lock` |
| ☐ | Build artifact | `uv build` |
| ☐ | Verify wheel tự chứa | mục 6 — demo PASS ngoài repo |
| ☐ | Verify image (khi có Docker) | `docker build` + smoke test mục 8 |
| ☐ | Cấu hình môi trường | `.agent/config.yaml` commit; secret ngoài repo |
| ☐ | Kiểm tra môi trường đích | `agent-kit doctor` → `Agent environment is ready.` |
| ☐ | Chạy thử end-to-end | `agent-kit run` → `agent-kit evaluate` → `Result: PASS` |
| ☐ | Kiro (nếu dùng) | `agent-kit kiro status` → `Kiro integration is complete.` |
| ☐ | Gate CI | exit code `run`/`evaluate` chặn deploy khi FAIL |
| ☐ | Lưu artifact để rollback | upload `dist/` + tag `v<version>` |
| ☐ | Bàn giao | `README.md`, `docs/uat-tutorial.md`, `docs/kiro-integration.md` |

---

## 15. Phụ lục — lệnh nhanh

```bash
# ---- Packaging ----
uv lock && uv lock --check
uv build                                   # dist/*.whl + dist/*.tar.gz
uv tool install dist/*.whl --force          # cài từ artifact
uv tool install '.[openai]' --force         # cài từ source kèm extras
uv run python -c "import agent_kit; print(agent_kit.__version__)"

# ---- Deployment ----
docker build -t agent-kit-poc:0.1.0 .
docker run --rm -v "$PWD:/work" --env-file .env agent-kit-poc:0.1.0 agent-kit doctor --project /work
uv tool install dist/agent_kit_poc-0.1.0-py3-none-any.whl --force    # rollback
uv tool uninstall agent-kit-poc

# ---- Kiểm tra sau deploy ----
agent-kit --version
agent-kit doctor --project ./demo
agent-kit run --project ./demo
agent-kit evaluate ./demo/output/sample-001.md
agent-kit kiro status --project ./demo
```

## 16. Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`uat-tutorial.md`](uat-tutorial.md) | Hướng dẫn cài đặt & sử dụng cho UAT (tiếng Việt) |
| [`architecture.md`](architecture.md) | Kiến trúc, mô hình bảo mật, extension seams |
| [`development.md`](development.md) | Setup dev, test, thêm model/tool/skill/workflow |
| [`kiro-integration.md`](kiro-integration.md) | Định dạng `.kiro/*` và xử lý sự cố Kiro |
| [`../Dockerfile`](../Dockerfile) | Định nghĩa image |
| [`../pyproject.toml`](../pyproject.toml) | Metadata, extras, force-include |
