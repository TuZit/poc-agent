# Hướng dẫn cài đặt & sử dụng — Tài liệu UAT

**Sản phẩm:** Agent Kit POC (`agent-kit`)
**Phiên bản:** 0.2.0
**Mục đích tài liệu:** hướng dẫn người kiểm thử (UAT tester) cài đặt, chạy thử và nghiệm thu bản POC.
**Thời lượng thực hiện dự kiến:** 30–45 phút (đã bao gồm cả phần Kiro).

---

## 1. Mục đích & phạm vi

Tài liệu này dùng để **nghiệm thu (UAT)** một POC: bộ AI Agent Kit có thể cài đặt được, lấy cảm hứng từ GitHub Spec Kit và tích hợp được với Kiro.

Phạm vi nghiệm thu gồm:

| # | Hạng mục | Mô tả ngắn |
|---|---|---|
| 1 | Cài đặt | Cài `agent-kit` như một CLI bằng `uv tool install` |
| 2 | Khởi tạo project | `agent-kit init` sinh project từ template |
| 3 | Cấu hình | `.agent/config.yaml` điều khiển model / tool / skill / workflow |
| 4 | Chạy agent | `agent-kit run` sinh output có cấu trúc |
| 5 | Đánh giá | `agent-kit evaluate` chấm điểm deterministic |
| 6 | Kiro | Sinh `.kiro/*` và expose runtime qua MCP server |
| 7 | An toàn | Tool bị giới hạn quyền (filesystem/shell) |

> **Ngoài phạm vi POC:** multi-agent, RBAC, Kubernetes, billing, vector database, UI, nhiều LLM provider. Không cần test các phần này.

**Đối tượng:** tester không cần biết code Python; chỉ cần dùng được Terminal.

---

## 2. Chuẩn bị môi trường

### 2.1 Yêu cầu bắt buộc

| Thành phần | Yêu cầu | Kiểm tra bằng lệnh |
|---|---|---|
| Hệ điều hành | macOS / Linux (Windows: dùng WSL) | — |
| Python | **3.11 trở lên** | `python3 --version` |
| `uv` | Bản mới nhất | `uv --version` |
| Terminal | Terminal / iTerm / VS Code terminal | — |
| `OPENAI_API_KEY` | **Chỉ cần nếu** test model thật | `echo $OPENAI_API_KEY` |

### 2.2 Cài `uv` (nếu chưa có)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"      # thêm vào ~/.zshrc để khỏi phải gõ lại
uv --version
```

Nếu chưa có Python 3.11+:

```bash
uv python install 3.12
```

> 💡 **Gặp lỗi `command not found: uv` hoặc `agent-kit`** → luôn chạy `export PATH="$HOME/.local/bin:$PATH"` trước, hoặc thêm dòng đó vào `~/.zshrc`.

### 2.3 Lấy source code

Toàn bộ source nằm trong thư mục `dsh-build/`. Tester cần đường dẫn tuyệt đối tới thư mục này, ví dụ:

```bash
cd /đường/dẫn/tới/poc-agent/dsh-build
pwd            # phải kết thúc bằng .../dsh-build
ls             # phải thấy pyproject.toml, src/, skills/, integrations/
```

---

## 3. Cài đặt Agent Kit

Chọn **cách 0** nếu máy bạn không có Python (chỉ cần Terminal). Chọn **cách A** nếu
chỉ test offline, **cách B** nếu muốn test với model thật.

### Cách 0 — Không cần Python (binary standalone)

```bash
# nếu đội phát hành đã có host release:
curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh

# hoặc cài thủ công từ file binary được cung cấp:
mkdir -p ~/.local/bin
cp agent-kit-darwin-arm64 ~/.local/bin/agent-kit    # đúng bản với máy bạn: uname -m
chmod +x ~/.local/bin/agent-kit
export PATH="$HOME/.local/bin:$PATH"
```

Kiểm tra: `agent-kit --version` → `agent-kit 0.2.0`. Toàn bộ phần còn lại của tài
liệu áp dụng y hệt. Chi tiết + xử lý sự cố macOS/Windows:
[`end-user-install.md`](end-user-install.md).

### Cách A — Bản offline (khuyến nghị cho UAT, không cần API key)

```bash
cd /đường/dẫn/tới/poc-agent/dsh-build
uv tool install . --force
```

### Cách B — Bản đầy đủ, có provider OpenAI

```bash
cd /đường/dẫn/tới/poc-agent/dsh-build
uv tool install '.[openai]' --force
```

### Kiểm tra cài đặt

```bash
agent-kit --version
```

**Kết quả mong đợi:**

```text
agent-kit 0.2.0
```

```bash
agent-kit --help
```

**Kết quả mong đợi:** danh sách lệnh gồm `init`, `doctor`, `run`, `evaluate`, `config`, `kiro`, `mcp`.

---

## 4. Khởi tạo project demo

```bash
mkdir -p ~/uat-agent-kit && cd ~/uat-agent-kit
agent-kit init demo-project --ai kiro
cd demo-project
```

**Kết quả mong đợi** (rút gọn):

```text
✓ Initialized agent-kit project in /Users/<bạn>/uat-agent-kit/demo-project
  + .agent/config.yaml
  + README.md
  + samples/requirement-analysis/expected/sample-001.md
  + samples/requirement-analysis/input/sample-001.md

✓ Kiro integration installed
  + .kiro/steering/agent-kit.md
  + .kiro/hooks/agent-kit-evaluate.json
  + .kiro/settings/mcp.json
  ...
```

Kiểm tra cấu trúc:

```bash
find . -type f -not -path "./.git/*" | sort
```

---

## 5. Cấu hình

File cấu hình duy nhất: `.agent/config.yaml`. **Không bao giờ đặt API key trong file này.**

```bash
agent-kit config show
agent-kit config get model.provider
agent-kit config set model.provider mock        # chạy offline
agent-kit config set model.name mock-model
agent-kit config set tools.shell.enabled true
```

**Kết quả mong đợi** của `config show`:

```yaml
agent:
  name: demo-project
model:
  provider: mock
  name: mock-model
tools:
  filesystem:
    enabled: true
  shell:
    enabled: true
skills:
- requirement-analysis
workflow:
  name: requirement-analysis
```

Nếu dùng model thật, key lấy từ biến môi trường:

```bash
export OPENAI_API_KEY="sk-..."          # dán key thật của bạn
agent-kit config set model.provider openai
agent-kit config set model.name gpt-4o-mini
```

---

## 6. Kiểm tra nhanh (smoke test) — 5 phút

Chạy tuần tự 4 lệnh sau, tất cả phải PASS:

```bash
# 1. Kiểm tra môi trường
agent-kit doctor

# 2. Chạy agent
agent-kit run

# 3. Xem output
cat output/sample-001.md

# 4. Chấm điểm output
agent-kit evaluate output/sample-001.md
```

### Kết quả mong đợi — `doctor`

```text
Agent Kit Doctor

✓ Agent Kit 0.2.0 (python package: .../site-packages/agent_kit)
✓ Python 3.11+ (3.12.14)
✓ Configuration (.agent/config.yaml)
✓ Configuration is valid
✓ Model configuration (mock/mock-model)
✓ OPENAI_API_KEY (not required for provider 'mock')
✓ Tools (filesystem, shell)
✓ Skill 'requirement-analysis'
✓ Workflow 'requirement-analysis'

Agent environment is ready.
```

### Kết quả mong đợi — `run`

```text
Running workflow 'requirement-analysis' — agent=demo-project model=mock/mock-model tools=filesystem, shell skills=requirement-analysis workflow=requirement-analysis
✓ Output written to output/sample-001.md
✓ Validation passed: all required sections present.

Next: agent-kit evaluate output/sample-001.md
```

### Kết quả mong đợi — `evaluate`

```text
Evaluation

✓ Output generated
✓ Objective
✓ Actors
✓ Functional Requirements
✓ Non-Functional Requirements
✓ Assumptions
✓ Open Questions

Result: PASS
```

Và `output/sample-001.md` phải có nội dung bắt đầu bằng `# Requirement Summary`.

---

## 7. Chạy với model thật (OpenAI)

Chỉ thực hiện nếu bạn có `OPENAI_API_KEY` (tester không có key thì **bỏ qua mục này**, không tính là Fail).

```bash
export OPENAI_API_KEY="sk-..."
agent-kit config set model.provider openai
agent-kit config set model.name gpt-4o-mini
agent-kit doctor                       # phải có ✓ OPENAI_API_KEY
agent-kit run --input samples/requirement-analysis/input/sample-001.md --output output/openai-run.md
agent-kit evaluate output/openai-run.md
```

**Lưu ý nghiệm thu:** nội dung do LLM sinh ra **không cần khớp chính xác** với `samples/.../expected/sample-001.md`. Chỉ cần:
1. có đủ 6 section bắt buộc,
2. `evaluate` trả về `Result: PASS`,
3. nội dung không bịa thêm thông tin không có trong input (các điểm chưa rõ phải nằm ở `Open Questions`).

---

## 8. Tích hợp Kiro

### 8.1 Cài / kiểm tra

```bash
agent-kit kiro install          # nếu chưa cài lúc init
agent-kit kiro status
```

**Kết quả mong đợi:**

```text
Kiro integration status

✓ .kiro/agents/agent-kit.json
✓ .kiro/agents/code-review.json
✓ .kiro/agents/unit-test.json
✓ .kiro/hooks/agent-kit-context.json
✓ .kiro/hooks/agent-kit-evaluate.json
✓ .kiro/hooks/agent-kit-orchestrate.json
✓ .kiro/hooks/agent-kit-run.json
✓ .kiro/prompts/agent-kit.code-review.md
✓ .kiro/prompts/agent-kit.evaluate.md
✓ .kiro/prompts/agent-kit.orchestrate.md
✓ .kiro/prompts/agent-kit.run.md
✓ .kiro/prompts/agent-kit.unit-test.md
✓ .kiro/settings/mcp.json
✓ .kiro/specs/agent-kit-poc/.config.kiro
✓ .kiro/specs/agent-kit-poc/design.md
✓ .kiro/specs/agent-kit-poc/requirements.md
✓ .kiro/specs/agent-kit-poc/tasks.md
✓ .kiro/steering/agent-kit-code-review.md
✓ .kiro/steering/agent-kit-requirements.md
✓ .kiro/steering/agent-kit-unit-test.md
✓ .kiro/steering/agent-kit.md

Kiro integration is complete.
```

### 8.2 Kiểm tra MCP server không cần mở Kiro

```bash
agent-kit mcp tools
```

**Kết quả mong đợi:** liệt kê 4 tool `agent_kit_run_workflow`, `agent_kit_evaluate`, `agent_kit_capabilities`, `agent_kit_read_skill`.

Gọi thử một tool:

```bash
agent-kit mcp call agent_kit_capabilities
agent-kit mcp call agent_kit_run_workflow --arguments '{"input_text": "Build a todo API with auth", "write_output": "output/uat.md"}'
agent-kit mcp call agent_kit_evaluate --arguments '{"output_file": "output/uat.md"}'
```

**Kết quả mong đợi:**

```text
workflow: requirement-analysis
valid: True
tool_calls: 0
written: output/uat.md
```

### 8.3 Kiểm tra giao thức MCP bằng tay (giống cách Kiro gọi)

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | agent-kit mcp serve
```

**Kết quả mong đợi (2 dòng JSON):** dòng 1 có `"serverInfo":{"name":"agent-kit","version":"0.2.0"}`; dòng 2 liệt kê đủ 6 tool.

### 8.4 Sử dụng trong Kiro IDE

1. Mở Kiro → **File → Open Folder** → chọn thư mục `demo-project`.
2. Mở panel **MCP** (hoặc `/mcp` trong Kiro CLI) → phải thấy server tên **`agent-kit`** đã kết nối, với 4 tool.
3. Kiểm tra **steering**: file `.kiro/steering/agent-kit.md` được nạp làm ngữ cảnh (Kiro hiển thị trong phần Steering/Context).
4. Kiểm tra **hooks**: panel Hooks phải có 3 hook của agent-kit:
   - `agent-kit: project capabilities` (khi gửi prompt)
   - `agent-kit: evaluate requirement summary on save` (khi lưu file `output/*.md`)
   - `agent-kit: run requirement analysis` (chạy tay)
5. Thử hội thoại: yêu cầu Kiro *"dùng tool agent_kit_run_workflow để phân tích yêu cầu trong samples/requirement-analysis/input/sample-001.md rồi lưu vào output/kiro-test.md"* → tool `agent_kit_run_workflow` phải được gọi và file được tạo.
6. Thử **custom agent**: trong terminal chạy `kiro-cli --agent agent-kit` (nếu đã cài Kiro CLI).

> ⚠️ Nếu Kiro không thấy tool: kiểm tra `which agent-kit` trong Terminal — Kiro phải kế thừa được `PATH` chứa lệnh này. Nếu không, sửa `.kiro/settings/mcp.json` để dùng đường dẫn tuyệt đối trong `command` (xem mục 11).

---

## 9. Kịch bản UAT (test cases)

Ghi kết quả vào cột cuối: **P** = Pass, **F** = Fail, kèm ghi chú nếu Fail.

### 9.1 Nhóm A — Cài đặt & khởi tạo

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-01 | Cài đặt CLI | `uv tool install . --force` → `agent-kit --version` | In ra `agent-kit 0.2.0` | ☐ |
| UAT-02 | Trợ giúp CLI | `agent-kit --help` | Liệt kê `init`, `doctor`, `config`, `run`, `evaluate`, `kiro`, `mcp` | ☐ |
| UAT-03 | Khởi tạo project | `agent-kit init demo-project --ai kiro` | Tạo `.agent/config.yaml`, `README.md`, `samples/`, `.kiro/` | ☐ |
| UAT-04 | *(Negative)* Chống ghi đè | Chạy lại `agent-kit init demo-project` | **Thoát mã 1**, báo "already exists", **không** thay đổi file nào | ☐ |
| UAT-05 | Ghi đè có chủ đích | `agent-kit init demo-project --force` | Thoát mã 0, file template được phục hồi, file lạ vẫn còn | ☐ |
| UAT-05b | *(chỉ khi dùng binary)* Không cần Python | `env -i HOME="$HOME" PATH=/usr/bin:/bin agent-kit --version` rồi `init`/`run`/`evaluate` | Mọi lệnh chạy được dù môi trường trống, `Result: PASS` | ☐ |

### 9.2 Nhóm B — Cấu hình & chẩn đoán

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-06 | Xem cấu hình | `agent-kit config show` | In YAML có `provider`, `tools`, `skills`, `workflow` | ☐ |
| UAT-07 | Đọc 1 giá trị | `agent-kit config get model.provider` | In `mock` (hoặc `openai`) | ☐ |
| UAT-08 | Sửa cấu hình | `agent-kit config set model.name other-model` rồi `config get model.name` | In `other-model` | ☐ |
| UAT-09 | Doctor khi sẵn sàng | `agent-kit config set model.provider mock` → `agent-kit doctor` | Tất cả ✓ và dòng `Agent environment is ready.`, thoát mã 0 | ☐ |
| UAT-10 | *(Negative)* Thiếu API key | `config set model.provider openai` → `agent-kit doctor` | Dòng `✗ OPENAI_API_KEY` kèm hướng dẫn, **thoát mã 1** | ☐ |
| UAT-11 | *(Negative)* Sai workflow | `config set workflow.name khong-ton-tai` → `doctor` | Báo `✗` kèm danh sách workflow hợp lệ; sau đó set lại `requirement-analysis` | ☐ |

### 9.3 Nhóm C — Chạy agent & đánh giá

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-12 | Chạy offline | `agent-kit run` | Tạo `output/sample-001.md`, báo "Validation passed" | ☐ |
| UAT-13 | Nội dung output | `cat output/sample-001.md` | Có `# Requirement Summary` và 6 section bắt buộc | ☐ |
| UAT-14 | Chấm điểm PASS | `agent-kit evaluate output/sample-001.md` | `Result: PASS`, thoát mã 0 | ☐ |
| UAT-15 | Input/output tùy chọn | `agent-kit run --input samples/requirement-analysis/input/sample-001.md --output output/custom.md` | Tạo `output/custom.md` | ☐ |
| UAT-16 | *(Negative)* Thiếu input | `agent-kit run --input khong-co.md` | Báo "Input file not found", **thoát mã 1** | ☐ |
| UAT-17 | *(Negative)* Output thiếu section | Tạo file `output/bad.md` chỉ chứa `# Requirement Summary` rồi `agent-kit evaluate output/bad.md` | Các section thiếu bị đánh `✗`, `Result: FAIL`, **thoát mã 1** | ☐ |
| UAT-18 | *(Negative)* File không tồn tại | `agent-kit evaluate output/khong-co.md` | `✗ Output generated — file not found`, thoát mã 1 | ☐ |
| UAT-19 | Kiểm tra concept | `agent-kit evaluate output/sample-001.md --require-concept blockchain` | `✗ Concept: blockchain`, `Result: FAIL` | ☐ |
| UAT-20 | Model thật *(tùy chọn)* | Mục 7 ở trên | `Result: PASS` với output do OpenAI sinh | ☐ |

### 9.4 Nhóm D — Kiro & MCP

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-21 | Cài lớp Kiro | `agent-kit kiro install` | Sinh đủ 21 file `.kiro/*` như mục 8.1 | ☐ |
| UAT-22 | Trạng thái Kiro | `agent-kit kiro status` | Tất cả ✓, dòng `Kiro integration is complete.`, thoát mã 0 | ☐ |
| UAT-23 | *(Negative)* Trạng thái khi thiếu | Xoá `.kiro/settings/mcp.json` → `agent-kit kiro status` | Dòng `✗ .../mcp.json`, **thoát mã 1**; chạy lại `kiro install` để phục hồi | ☐ |
| UAT-24 | Không ghi đè file đã sửa | Sửa `.kiro/steering/agent-kit.md` thành nội dung riêng → `agent-kit kiro install` | Nội dung riêng **vẫn còn** | ☐ |
| UAT-25 | Ghi đè khi có `--force` | `agent-kit kiro install --force` | Steering trở về nội dung template | ☐ |
| UAT-26 | Liệt kê MCP tool | `agent-kit mcp tools` | Đủ 6 tool (gồm `agent_kit_orchestrate`, `agent_kit_list_agents`) | ☐ |
| UAT-27 | Gọi MCP tool | `agent-kit mcp call agent_kit_capabilities` | In cấu hình đang dùng (model, tools, skills, workflow) | ☐ |
| UAT-28 | MCP handshake | Lệnh `printf ... \| agent-kit mcp serve` ở mục 8.3 | 2 dòng JSON hợp lệ, có `serverInfo` và 6 tool | ☐ |
| UAT-29 | Lưu ý an toàn MCP | `cat .kiro/settings/mcp.json` | `autoApprove` **không** chứa `agent_kit_run_workflow`/`agent_kit_orchestrate` | ☐ |
| UAT-30 | Dùng trong Kiro IDE | Mục 8.4 | Kiro thấy server `agent-kit`, tool chạy được, tạo file output | ☐ |

### 9.5 Nhóm E — An toàn & chất lượng

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-31 | Toàn bộ test suite | `cd dsh-build && uv run pytest` | `252 passed`, **không cần** `OPENAI_API_KEY`, không cần mạng | ☐ |
| UAT-32 | Filesystem bị giới hạn | `uv run pytest tests/unit/test_tools.py -k traversal` | Test PASS: ghi ra ngoài project root bị từ chối | ☐ |
| UAT-33 | Shell bị giới hạn | `uv run pytest tests/unit/test_tools.py -k whitelist` | Test PASS: lệnh ngoài whitelist (`bash`, `echo`...) bị từ chối | ☐ |
| UAT-34 | Không lộ secret | `cat .agent/config.yaml` | Không có API key trong file; key chỉ nằm ở biến môi trường | ☐ |
| UAT-35 | Chạy không cần API key | `unset OPENAI_API_KEY` → `agent-kit config set model.provider mock` → `agent-kit run` | Vẫn chạy thành công | ☐ |

---

### 9.6 Nhóm F — Đa agent & orchestrator

| ID | Kịch bản | Các bước | Kết quả mong đợi | KQ |
|---|---|---|---|---|
| UAT-36 | Danh sách agent | `agent-kit agents` | In 3 agent (`requirement-analysis`, `code-review`, `unit-test-generation`), contract từng agent, dòng `Orchestrator: workflow=orchestration ... strategy=auto` | ☐ |
| UAT-37 | Agent code review | `agent-kit run --workflow code-review` | Tạo `output/sample-code-review.md`, có `# Code Review` + 4 section (Summary, Findings, Recommendations, Open Questions), "Validation passed" | ☐ |
| UAT-38 | Agent unit test | `agent-kit run --workflow unit-test-generation` | Tạo `output/sample-unit-test.md`, có `# Unit Test Plan` + 5 section (Summary, Test Scope, Test Cases, Edge Cases, Open Questions) | ☐ |
| UAT-39 | Orchestrator tự chọn agent | `agent-kit run --workflow orchestration` | In `Orchestrator selected: code-review, unit-test-generation`, tạo `output/sample-orchestration.md` có `## Request Analysis`, `## Agent: Code Review`, `## Agent: Unit Test Generation`, `## Summary` | ☐ |
| UAT-40 | Ép agent | `agent-kit run --workflow orchestration --agents code-review` | Chỉ chạy code-review: báo cáo **không** có `## Agent: Unit Test Generation` | ☐ |
| UAT-41 | *(Negative)* Agent sai tên | `agent-kit run --workflow orchestration --agents khong-ton-tai` | Thoát mã 1, báo `Unknown agent`, liệt kê agent hợp lệ | ☐ |
| UAT-42 | *(Negative)* Strategy sai | `agent-kit run --workflow orchestration --strategy llm` | Thoát mã 1, báo `Unknown orchestrator strategy` | ☐ |
| UAT-43 | Chấm điểm theo contract agent | `agent-kit evaluate output/sample-code-review.md --workflow code-review` | `Result: PASS`; nếu chạy **không** có `--workflow` → FAIL (thiếu section Objective) | ☐ |
| UAT-44 | Slash command / custom agent trong Kiro | Trong Kiro: chạy prompt `agent-kit.code-review`; hoặc `kiro-cli --agent code-review` | Kiro gọi tool `agent_kit_run_workflow` với `workflow=code-review` và tạo báo cáo | ☐ |
| UAT-45 | *(Negative)* Thiếu API key với agent thật | `config set model.provider openai`, unset key, `agent-kit run --workflow code-review` | Thoát mã 1, báo thiếu `OPENAI_API_KEY` (không crash) | ☐ |

> Ghi chú nghiệm thu: với `model.provider: mock`, nội dung do agent sinh ra là **cố định**
> (mock trả output theo skill) nên có thể so khớp với `samples/<agent>/expected/`.
> Với model thật, chỉ cần đủ section + `Result: PASS` (xem mục 7).

## 10. Tiêu chí nghiệm thu

**PASS toàn bộ** khi:

1. 100% test case **bắt buộc** Pass — tức tất cả trừ `UAT-20` (model thật, tùy chọn).
2. `agent-kit doctor` báo `Agent environment is ready.` ở cấu hình `mock`.
3. `agent-kit evaluate output/sample-001.md` trả `Result: PASS`.
4. `agent-kit kiro status` trả `Kiro integration is complete.`
5. `uv run pytest` trả `252 passed` **khi đã unset `OPENAI_API_KEY`** (chứng minh test offline).
6. Nhóm F: orchestrator tự chọn đúng agent và báo cáo tổng hợp đủ section.
7. Không có lỗi crash/traceback Python nào khi chạy các kịch bản trên (ngoại trừ các negative test được mô tả là phải thoát mã 1 với thông báo thân thiện).

**FAIL** nếu: có traceback Python thô, CLI treo, ghi được ra ngoài project root, thực thi được lệnh ngoài whitelist, hoặc file cấu hình chứa secret.

---

## 11. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `command not found: agent-kit` | `~/.local/bin` chưa có trong PATH | `export PATH="$HOME/.local/bin:$PATH"` (thêm vào `~/.zshrc`) |
| macOS chặn binary: *"developer cannot be verified"* | File tải bằng trình duyệt bị gắn cờ cách ly | `xattr -d com.apple.quarantine ~/.local/bin/agent-kit` |
| `bad CPU type in executable` | Tải nhầm bản Intel/Apple Silicon | Kiểm tra `uname -m` rồi lấy đúng bản (`arm64` / `x86_64`) |
| `command not found: uv` | Chưa cài `uv` | Chạy lại mục 2.2 |
| `Configuration not found at .../.agent/config.yaml` | Đang chạy ngoài thư mục project | `cd demo-project`, hoặc thêm `--project /đường/dẫn/project` |
| `OPENAI_API_KEY is not set` | Dùng provider `openai` nhưng chưa export key | `export OPENAI_API_KEY=...` hoặc `agent-kit config set model.provider mock` |
| `The optional 'openai' package is not installed` | Cài thiếu extras | `uv tool install '.[openai]' --force` |
| `Skill 'x' not found` | Sai tên skill | Lệnh sẽ in danh sách skill khả dụng + đường dẫn đã tìm |
| `Agent did not produce a final answer within 8 iterations` | Model thật gọi tool lặp | Chạy lại; nếu lặp lại, ghi nhận vào báo cáo UAT (đây là lỗi cần báo dev) |
| `Invalid YAML in .../config.yaml` | Sửa file cấu hình sai cú pháp | `agent-kit init demo-project --force` để phục hồi template |
| Kiro không thấy MCP server | Kiro không kế thừa PATH | Sửa `.kiro/settings/mcp.json`: đặt `"command"` thành đường dẫn tuyệt đối, ví dụ `"/Users/<bạn>/.local/bin/agent-kit"` |
| Hook của Kiro không chạy | File hook sai định dạng | Chỉ dùng `.kiro/hooks/*.json` (schema `version: "v1"`). File `.kiro.hook` cũ **không** được Kiro 1.0 đọc |
| `ruff`/`pytest` chưa có | Chưa sync môi trường dev | `cd dsh-build && uv sync --all-extras` |

---

## 12. Mẫu báo cáo kết quả UAT

Tạo file `UAT-RESULT.md` với nội dung sau và điền khi test:

```markdown
# Báo cáo kết quả UAT — Agent Kit POC v0.2.0

- Người test:
- Ngày test:
- Hệ điều hành / phiên bản Python:
- Provider đã dùng: mock / openai (model: ............)
- Commit hash: `git -C /đường/dẫn/tới/dsh-build rev-parse --short HEAD`

## Tổng hợp

| Nhóm | Tổng số case | Pass | Fail |
|---|---|---|---|
| A — Cài đặt & khởi tạo | 5 | | |
| B — Cấu hình & chẩn đoán | 6 | | |
| C — Chạy agent & đánh giá | 9 | | |
| D — Kiro & MCP | 10 | | |
| E — An toàn & chất lượng | 5 | | |

## Case thất bại

| ID | Mô tả lỗi | Bước tái hiện | Mức độ (Cao/TB/Thấp) | Ảnh/log |
|---|---|---|---|---|
| | | | | |

## Kết luận

- [ ] PASS — đủ tiêu chí nghiệm thu (mục 10)
- [ ] FAIL — còn lỗi chặn

## Ghi chú / đề xuất
```

---

## 13. Phụ lục — Cheat sheet lệnh

```bash
# Cài đặt
uv tool install '.[openai]' --force      # chạy trong dsh-build/
agent-kit --version

# Khởi tạo & cấu hình
agent-kit init demo-project --ai kiro
agent-kit doctor
agent-kit config show
agent-kit config get model.provider
agent-kit config set model.provider mock

# Chạy & đánh giá
agent-kit agents
agent-kit run
agent-kit run --workflow code-review
agent-kit run --workflow orchestration --agents code-review
agent-kit run --input <file> --output <file>
agent-kit evaluate output/sample-001.md
agent-kit evaluate output/sample-code-review.md --workflow code-review
agent-kit evaluate output/sample-001.md --require-concept "create product"

# Kiro
agent-kit kiro install | status | uninstall

# MCP
agent-kit mcp tools
agent-kit mcp call agent_kit_capabilities
agent-kit mcp call agent_kit_run_workflow --arguments '{"input_text": "...", "write_output": "output/x.md"}'
agent-kit mcp serve

# Test suite
cd dsh-build && uv run pytest
cd dsh-build && uv run ruff check src tests
```

### Cấu trúc project sau khi `init`

```text
demo-project/
├── .agent/
│   └── config.yaml                 # cấu hình duy nhất (KHÔNG chứa secret)
├── .kiro/                          # lớp tích hợp Kiro
│   ├── steering/  hooks/  agents/  prompts/  settings/  specs/
├── samples/requirement-analysis/
│   ├── input/sample-001.md         # input mẫu
│   └── expected/sample-001.md      # output tham chiếu (không cần khớp tuyệt đối)
├── output/                         # sinh ra khi `agent-kit run`
└── README.md
```

### 6 section bắt buộc của một Requirement Summary

`Objective` · `Actors` · `Functional Requirements` · `Non-Functional Requirements` · `Assumptions` · `Open Questions`

(Thiếu bất kỳ section nào → `agent-kit evaluate` trả `FAIL`.)

---

## 14. Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`../README.md`](../README.md) | Tổng quan sản phẩm, kiến trúc, hướng dẫn mở rộng |
| [`end-user-install.md`](end-user-install.md) | Cài đặt cho người dùng không có Python (binary, 1 lệnh) |
| [`packaging-deployment.md`](packaging-deployment.md) | Đóng gói (wheel/binary/Docker) và triển khai (CI/CD, secret, rollback) |
| [`multi-agent.md`](multi-agent.md) | 3 specialist agent + orchestrator: routing, CLI/MCP/Kiro, cách thêm agent |
| [`agent-integrations.md`](agent-integrations.md) | Kiến trúc tích hợp agent tool (hiện tại: Kiro) |
| [`architecture.md`](architecture.md) | Kiến trúc phân lớp, mô hình bảo mật |
| [`development.md`](development.md) | Hướng dẫn cho developer (setup, test, thêm model/tool/skill/workflow) |
| [`kiro-integration.md`](kiro-integration.md) | Chi tiết định dạng file Kiro và xử lý sự cố Kiro |
| [`../specs/001-agent-kit-poc/spec.md`](../specs/001-agent-kit-poc/spec.md) | Yêu cầu chức năng & tiêu chí chấp nhận gốc |
