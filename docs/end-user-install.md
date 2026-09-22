# Cài đặt cho người dùng cuối (không cần Python)

**Dành cho:** tester / người dùng chỉ muốn dùng `agent-kit`, không quan tâm Python, pip hay uv.

Bạn **không cần** cài Python. Có 3 cách, chọn cách phù hợp:

| Cách | Cần gì | Khi nào dùng |
|---|---|---|
| **A. Binary standalone** (khuyến nghị) | Chỉ cần Terminal | Hầu hết người dùng — cài 1 lệnh, chạy ngay |
| **B. Docker** | Docker Desktop | Máy đã có Docker, muốn cô lập hoàn toàn |
| **C. uv tool / pipx** | Python 3.11+ | Dev muốn dùng source, hoặc cần nhúng vào Python khác |

> Toàn bộ binary đã đóng gói sẵn runtime, skill, template project và lớp tích hợp Kiro.
> Không cần mạng sau khi cài (trừ khi dùng model thật OpenAI).

---

## Cách A — Binary standalone (khuyến nghị)

### A.1 Cài bằng 1 lệnh (macOS / Linux)

```bash
curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh
```

> ⚠️ `YOUR-HOST` là nơi đội phát hành đặt file. Nếu chưa có, dùng **A.3 (cài thủ công)** —
> chỉ cần file binary và 3 lệnh.

Script sẽ:
1. nhận diện hệ điều hành + CPU (macOS/Linux, arm64/x86_64),
2. tải `agent-kit-<os>-<arch>` về `~/.local/bin/agent-kit`,
3. cấp quyền chạy, kiểm tra `--version`, và nhắc thêm vào `PATH` nếu cần.

Cài phiên bản cụ thể / thư mục khác:

```bash
AGENT_KIT_VERSION=0.2.0 AGENT_KIT_INSTALL_DIR="$HOME/bin" \
  curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh
```

Thêm vào `PATH` (nếu script nhắc):

```bash
export PATH="$HOME/.local/bin:$PATH"     # thêm vào ~/.zshrc để giữ lâu dài
```

### A.2 Cài trên Windows (PowerShell)

```powershell
irm https://YOUR-HOST/agent-kit/install.ps1 | iex
```

Script tải `agent-kit-windows-<arch>.exe` vào `%LOCALAPPDATA%\Programs\agent-kit`
và thêm thư mục đó vào `PATH` của user.

> ⚠️ **Trạng thái:** Windows **chưa được build/kiểm chứng** trong phase này. Binary
> hiện có: `darwin-arm64`, `darwin-x86_64`, `linux-x86_64`, `linux-arm64`.
> Muốn có bản Windows, người phát hành chạy mục 7.1 trên máy Windows.

### A.3 Cài thủ công (không cần script)

1. Nhận file binary từ đội phát hành (ví dụ `agent-kit-darwin-arm64`).
2. Copy vào một thư mục trong `PATH`:

```bash
mkdir -p ~/.local/bin
cp agent-kit-darwin-arm64 ~/.local/bin/agent-kit
chmod +x ~/.local/bin/agent-kit
export PATH="$HOME/.local/bin:$PATH"
```

3. Kiểm tra:

```bash
agent-kit --version
```

**Kết quả mong đợi:**

```text
agent-kit 0.2.0
```

### A.4 Cập nhật / gỡ cài

```bash
# cập nhật: chạy lại installer với version mới
AGENT_KIT_VERSION=0.2.0 curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh

# gỡ cài
rm ~/.local/bin/agent-kit
```

### A.5 Máy nào chạy được?

| Nền tảng | Binary | Ghi chú |
|---|---|---|
| macOS Apple Silicon (M1/M2/M3/M4) | `agent-kit-darwin-arm64` | đã build & kiểm chứng |
| macOS Intel | `agent-kit-darwin-x86_64` | build được trên máy Intel |
| Linux x86_64 | `agent-kit-linux-x86_64` | build trên runner Linux |
| Linux arm64 | `agent-kit-linux-arm64` | build trên runner arm64 |
| Windows | `agent-kit-windows-x86_64.exe` | chưa build trong phase này |

Kích thước binary ~20 MB, chạy độc lập — không cần Python, `pip`, `uv` hay thư viện hệ thống.

---

## Cách B — Docker

Nếu máy đã có Docker Desktop:

```bash
docker run --rm -v "$PWD:/work" agent-kit-poc:0.2.0 agent-kit --help
docker run --rm -v "$PWD:/work" -e OPENAI_API_KEY agent-kit-poc:0.2.0 \
  agent-kit run --project /work
```

Chi tiết build image và các biến thể: [`packaging-deployment.md`](packaging-deployment.md) mục 8.

---

## Cách C — Dành cho dev (uv tool / pipx)

```bash
uv tool install 'agent-kit-poc[openai]'
# hoặc
pipx install 'agent-kit-poc[openai]'
```

Xem [`packaging-deployment.md`](packaging-deployment.md) mục 7 để biết đủ 5 kênh phân phối.

---

## 3. Dùng ngay sau khi cài

```bash
# 1. Tạo project (kèm tích hợp Kiro)
agent-kit init my-project --ai kiro
cd my-project

# 2. Kiểm tra môi trường
agent-kit doctor

# 3. Chọn model: mock = chạy offline, không cần API key
agent-kit config set model.provider mock

# 4. Chạy agent
agent-kit run

# 5. Chấm điểm kết quả
agent-kit evaluate output/sample-001.md
```

**Kết quả mong đợi:** `Agent environment is ready.` → `Result: PASS`.

Dùng model thật (OpenAI):

```bash
export OPENAI_API_KEY="sk-..."
agent-kit config set model.provider openai
agent-kit config set model.name gpt-4o-mini
agent-kit run
```

> API key **không bao giờ** được ghi vào file cấu hình; nó chỉ tồn tại trong biến
> môi trường của phiên Terminal.

Hướng dẫn sử dụng đầy đủ + bộ test case nghiệm thu: [`uat-tutorial.md`](uat-tutorial.md).

---

## 4. Xử lý sự cố

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `command not found: agent-kit` | `~/.local/bin` chưa trong `PATH` | `export PATH="$HOME/.local/bin:$PATH"` (thêm vào `~/.zshrc`) |
| macOS: *"cannot be opened because the developer cannot be verified"* | File tải bằng trình duyệt bị gắn cờ cách ly | `xattr -d com.apple.quarantine ~/.local/bin/agent-kit` |
| `Permission denied` khi chạy | Thiếu quyền thực thi | `chmod +x ~/.local/bin/agent-kit` |
| `bad CPU type in executable` | Sai kiến trúc (Intel vs Apple Silicon) | Tải đúng bản: `uname -m` → `arm64` hoặc `x86_64` |
| `✗ Unsupported operating system` khi cài | HĐH không nằm trong danh sách | Dùng Docker (cách B) |
| `curl: (22) ... 404` | Sai `AGENT_KIT_VERSION` hoặc chưa có bản phát hành | Kiểm tra lại version với đội phát hành |
| `Configuration not found at .../.agent/config.yaml` | Đang chạy ngoài thư mục project | `cd my-project` hoặc thêm `--project <đường dẫn>` |
| `OPENAI_API_KEY is not set` | Dùng provider `openai` nhưng chưa export | `export OPENAI_API_KEY=...` hoặc `agent-kit config set model.provider mock` |
| Lần chạy đầu chậm (~1–2 giây) | Binary tự giải nén runtime | Bình thường với bản one-file |

---

## 5. Người dùng cuối KHÔNG cần

- Python, `pip`, `uv`, `virtualenv`
- Quyền admin (cài vào `~/.local/bin`)
- Internet sau khi cài (trừ khi dùng model thật)
- Git — chỉ cần file binary hoặc 1 lệnh `curl`

---

## 6. Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`uat-tutorial.md`](uat-tutorial.md) | Hướng dẫn cài & sử dụng chi tiết cho UAT (35 test case) |
| [`kiro-integration.md`](kiro-integration.md) | Dùng agent-kit trong Kiro (steering, hooks, MCP) |
| [`packaging-deployment.md`](packaging-deployment.md) | Đóng gói & triển khai cho dev/DevOps |
| [`agent-integrations.md`](agent-integrations.md) | Thêm tích hợp cho agent tool khác (Claude Code, Copilot, Codex…) |

---

## 7. Dành cho người phát hành (maintainer)

### 7.1 Build binary

```bash
cd dsh-build
bash scripts/build-binary.sh
# → dist/bin/agent-kit-darwin-arm64   (hoặc linux-x86_64 tuỳ máy)
```

Script tự: sync group `package` + extra `openai`, chạy PyInstaller theo
`packaging/agent-kit.spec`, đổi tên artifact theo nền tảng.

Trên Windows (PowerShell):

```powershell
uv sync --extra openai --group package
uv run --extra openai --group package pyinstaller packaging/agent-kit.spec --noconfirm --clean
Rename-Item dist\agent-kit.exe agent-kit-windows-x86_64.exe
```

### 7.2 Kiểm tra binary trước khi phát hành

Phải chạy được khi **không có Python** trong môi trường:

```bash
BIN=dist/bin/agent-kit-darwin-arm64
env -i HOME="$HOME" PATH=/usr/bin:/bin "$BIN" --version

rm -rf /tmp/release-check && mkdir -p /tmp/release-check && cd /tmp/release-check
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" init demo --ai kiro
cd demo
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" config set model.provider mock
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" doctor
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" run
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" evaluate output/sample-001.md
env -i HOME="$HOME" PATH=/usr/bin:/bin "$OLDPWD/$BIN" kiro status
```

Kiểm tra MCP handshake bằng binary:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | "$BIN" mcp serve 2>/dev/null
```

### 7.3 Phát hành

```bash
# 1. Đặt tên artifact theo đúng quy ước mà install.sh mong đợi
#    agent-kit-darwin-arm64, agent-kit-darwin-x86_64,
#    agent-kit-linux-x86_64, agent-kit-linux-arm64, agent-kit-windows-x86_64.exe
# 2. Upload vào:  <AGENT_KIT_BASE_URL>/v<version>/
# 3. Upload packaging/install.sh và packaging/install.ps1 lên host tài liệu
# 4. Thay YOUR-HOST trong docs/end-user-install.md bằng URL thật
```

Ví dụ với GitHub Releases (base URL mặc định trong `install.sh`):

```bash
gh release create v0.2.0 \
  dist/bin/agent-kit-darwin-arm64 \
  dist/bin/agent-kit-linux-x86_64 \
  --title "Agent Kit POC v0.2.0"
```

### 7.4 Checklist phát hành binary

| ☐ | Việc | Lệnh / tiêu chí |
|---|---|---|
| ☐ | Test suite xanh | `uv run pytest` |
| ☐ | Lint sạch | `uv run ruff check src tests` |
| ☐ | Version đã bump | `src/agent_kit/__init__.py` |
| ☐ | Build binary | `bash scripts/build-binary.sh` |
| ☐ | Kiểm tra với `env -i` | mục 7.2 — tất cả PASS |
| ☐ | MCP handshake OK | mục 7.2 |
| ☐ | Artifact đặt đúng tên + đúng thư mục version | mục 7.3 |
| ☐ | `install.sh` chạy thử từ host thật | `curl -fsSL .../install.sh \| sh` |
| ☐ | Bản cài sạch chạy được demo | `init --ai kiro` → `run` → `evaluate` PASS |
