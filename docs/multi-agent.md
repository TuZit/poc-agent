# Các agent & Orchestrator

Bộ kit có **3 specialist agent** (mỗi agent = 1 skill + 1 workflow + 1 output contract)
và **1 orchestrator** ("agent lớn") phân tích yêu cầu rồi chọn agent phù hợp để chạy.

```text
                        ┌──────────────────────────────┐
   request ────────────►│  Orchestrator (orchestration)│
 (diff, requirement,    │  TaskRouter: phân tích tín hiệu│
  code, câu hỏi trộn)   └──────────────┬───────────────┘
                                       │ chọn 0..n agent
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
   ┌────────────────────┐   ┌────────────────────┐   ┌──────────────────────┐
   │ requirement-analysis│   │    code-review     │   │ unit-test-generation │
   │ SKILL.md + contract │   │ SKILL.md + contract│   │ SKILL.md + contract  │
   └─────────┬──────────┘   └─────────┬──────────┘   └──────────┬───────────┘
             └────────────────────────┼─────────────────────────┘
                                      ▼
                    # Agent Orchestration Report (1 báo cáo tổng hợp)
                                      ▼
                          Evaluate (deterministic) → PASS/FAIL
```

---

## 1. Ba specialist agent

| Agent (`--workflow`) | Dùng khi nào | Output contract (section bắt buộc) | Sample input |
|---|---|---|---|
| `requirement-analysis` | Có requirement / user story / feature cần phân tích | Objective, Actors, Functional Requirements, Non-Functional Requirements, Assumptions, Open Questions | `samples/requirement-analysis/input/sample-001.md` |
| `code-review` | Có diff / patch / file cần review | Summary, Findings, Recommendations, Open Questions | `samples/code-review/input/sample-code-review.md` |
| `unit-test-generation` | Cần test plan / test case cho 1 đơn vị code | Summary, Test Scope, Test Cases, Edge Cases, Open Questions | `samples/unit-test-generation/input/sample-unit-test.md` |

Mỗi agent có:

- **Skill**: `skills/<agent>/SKILL.md` — hiện là **skeleton**, team tự điền chuẩn thật
  (mỗi file có mục `## TODO (team to complete)`). Project có thể override bằng
  `.agent/skills/<agent>/SKILL.md`.
- **Workflow**: đăng ký trong `src/agent_kit/workflow/registry.py` với metadata
  (title, description, `required_sections`, `routing_keywords`, `default_input`).
- **Sample**: input + expected (expected chỉ để tham chiếu, không so khớp tuyệt đối).

---

## 2. Orchestrator hoạt động thế nào

### 2.1 Phân tích & lựa chọn (TaskRouter — deterministic)

`agent_kit.routing.TaskRouter` chấm điểm yêu cầu theo:

1. **Keyword** của từng agent (`routing_keywords`). Keyword ≤ 3 ký tự phải khớp
   nguyên từ (nên `pr` không khớp "product", `ut` không khớp "output").
2. **Tín hiệu cấu trúc**: `@@`, `+++ `, `diff --git`, ```` ```diff ```` → code review;
   `def test_`, `assert `, `pytest.mark`, `describe(`, `it(` → unit test.
3. Agent có ≥ 1 tín hiệu thì được chọn; sắp xếp theo **số tín hiệu giảm dần**, bằng
   nhau thì theo thứ tự trong config.
4. Không khớp gì → dùng `orchestrator.default_agents` (mặc định `requirement-analysis`).

Ví dụ thật (từ sample orchestration):

```text
- strategy: auto
- selection: 2 intent(s) detected: code-review, unit-test-generation
- signals for code-review: diff, refactor, diff code block
- signals for unit-test-generation: unit test, unit tests, pytest
- selected agents: code-review, unit-test-generation
```

Vì sao dùng rule-based thay vì gọi LLM để "plan"? Vì routing phải **tái lập được,
test được offline, miễn phí và giải thích được** (báo cáo in ra lý do chọn). Muốn
LLM tự chọn thì đã có sẵn ở tầng Kiro/Copilot/Claude qua MCP tools (mục 4).

### 2.2 Điều phối & tổng hợp

`OrchestrationWorkflow`:

1. đọc `orchestrator.strategy` (`auto` | `all`) và allow-list `orchestrator.agents`;
2. chọn agent (hoặc dùng `--agents` để ép);
3. chạy lần lượt từng agent qua `runtime.run_specialist(...)` (mỗi agent tự load skill
   của mình, tự gọi model, tự validate);
4. tổng hợp thành **một** báo cáo `# Agent Orchestration Report` gồm
   `## Request Analysis`, một `## Agent: <tên>` cho mỗi agent và `## Summary`
   (PASS/FAIL từng agent);
5. hợp lệ chỉ khi báo cáo đủ section **và** mọi agent con hợp lệ. Agent con fail thì
   issue được ghi rõ dạng `code-review: Missing required section: ...`.

`planner: rules` là giá trị duy nhất được hỗ trợ hiện tại; `planner: llm` sẽ báo lỗi
rõ ràng (đây là seam để mở rộng sau).

---

## 3. Chạy trên CLI

```bash
# xem danh sách agent + cấu hình orchestrator + sample
agent-kit agents

# chạy 1 agent (input mặc định = sample của chính nó)
agent-kit run --workflow code-review
agent-kit run --workflow unit-test-generation
agent-kit run --workflow requirement-analysis

# chạy orchestrator: tự chọn agent theo yêu cầu
agent-kit run --workflow orchestration \
  --input samples/orchestration/input/sample-orchestration.md \
  --output output/sample-orchestration.md

# ép agent / ép chiến lược
agent-kit run --workflow orchestration --agents code-review,unit-test-generation
agent-kit run --workflow orchestration --strategy all

# chấm điểm theo đúng contract của agent
agent-kit evaluate output/sample-code-review.md --workflow code-review
agent-kit evaluate output/sample-orchestration.md --workflow orchestration
```

Đặt orchestrator làm mặc định cho project:

```bash
agent-kit config set workflow.name orchestration
```

---

## 4. Dùng trong Kiro (slash command + custom agent + MCP)

### 4.1 Slash command (file prompt trong `.kiro/prompts/`)

`agent-kit kiro install` sinh sẵn 5 prompt:

| Prompt | Việc |
|---|---|
| `agent-kit.orchestrate.md` | để orchestrator tự chọn agent |
| `agent-kit.code-review.md` | chạy agent code review |
| `agent-kit.unit-test.md` | chạy agent unit test |
| `agent-kit.run.md` | chạy agent requirement analysis |
| `agent-kit.evaluate.md` | chấm điểm output |

### 4.2 Custom agent (`.kiro/agents/*.json`)

| Agent | Vai trò |
|---|---|
| `agent-kit` | orchestrator: phân tích, chọn agent, tổng hợp |
| `code-review` | chuyên review diff/patch |
| `unit-test` | chuyên sinh test plan |

```bash
kiro-cli --agent agent-kit        # orchestrator
kiro-cli --agent code-review      # chỉ review
kiro-cli --agent unit-test        # chỉ test plan
```

### 4.3 MCP tools

| Tool | Dùng khi |
|---|---|
| `agent_kit_list_agents` | cần biết có agent nào, khi nào dùng, contract ra sao |
| `agent_kit_orchestrate` | để orchestrator chọn agent và chạy (1 báo cáo tổng hợp) |
| `agent_kit_run_workflow` | ép chạy 1 agent (`workflow=code-review`, ...) |
| `agent_kit_evaluate` | chấm điểm output (theo `workflow`) |
| `agent_kit_capabilities` | cấu hình đang dùng (model, tools, skills, workflow, orchestrator) |
| `agent_kit_read_skill` | đọc toàn bộ instruction của skill |

`autoApprove` chỉ gồm 4 tool chỉ-đọc (`list_agents`, `capabilities`, `evaluate`,
`read_skill`); `run_workflow` và `orchestrate` vẫn cần người dùng xác nhận vì chúng
gọi model và ghi file. Chi tiết: [`kiro-integration.md`](kiro-integration.md).

### 4.4 Steering

4 file steering (`.kiro/steering/`): `agent-kit.md` (`always` — bản đồ + 3 agent),
`agent-kit-requirements.md`, `agent-kit-code-review.md`, `agent-kit-unit-test.md`
(`fileMatch` — contract theo loại file đang mở).

---

## 5. Cấu hình

```yaml
# .agent/config.yaml
skills:
  - requirement-analysis
  - code-review
  - unit-test-generation

workflow:
  name: requirement-analysis      # hoặc: orchestration | code-review | unit-test-generation

orchestrator:
  strategy: auto                  # auto = route theo tín hiệu | all = chạy mọi agent
  planner: rules                  # chỉ hỗ trợ rules (seam cho LLM planner sau này)
  agents:                         # allow-list + thứ tự chạy
    - requirement-analysis
    - code-review
    - unit-test-generation
  default_agents:                 # dùng khi auto không thấy tín hiệu nào
    - requirement-analysis
```

Kiểm tra cấu hình: `agent-kit doctor` (có check `Orchestrator agents (...)`),
`agent-kit config show`, `agent-kit agents`.

---

## 6. Thêm 1 agent mới (khoảng 20 phút)

1. **Skill** (Markdown, không cần Python):

```bash
mkdir -p skills/api-validation
$EDITOR skills/api-validation/SKILL.md     # nêu rõ Output Format + section bắt buộc
```

2. **Workflow**: thêm class vào `src/agent_kit/workflow/specialists.py`:

```python
class ApiValidationWorkflow(SkillWorkflow):
    name = "api-validation"
    title = "API Validation"
    description = "Validate an API description against the implementation."
    default_skill = "api-validation"
    required_sections = ("Summary", "Checks", "Findings", "Open Questions")
    routing_keywords = ("api validation", "openapi", "swagger", "endpoint contract")
    default_input = "samples/api-validation/input/sample-api.md"
```

3. **Đăng ký**: thêm 1 dòng vào `WORKFLOW_REGISTRY` trong
   `src/agent_kit/workflow/registry.py`.

4. **Config**: thêm tên agent vào `orchestrator.agents` (và `skills`).

5. **Sample**: thêm `samples/api-validation/input/*.md` (+ `expected/` nếu muốn).

6. **Test**: thêm case vào `tests/unit/test_orchestration.py` (agent được chọn với
   input phù hợp, output hợp lệ).

Agent mới tự động có: `agent-kit run --workflow api-validation`,
`agent-kit agents`, `evaluate --workflow api-validation`, tool MCP
`agent_kit_run_workflow`, và orchestrator có thể chọn nó.

7. (Tuỳ chọn) Kiro: thêm `.kiro/prompts/agent-kit.api-validation.md` và
   `.kiro/agents/api-validation.json` trong `integrations/kiro/`.

---

## 7. Ranh giới & việc còn lại

- **Skill 2 agent mới đang là skeleton**: cần team điền chuẩn review/testing thật
  (mỗi `SKILL.md` có checklist `## TODO`).
- **Orchestration hiện chạy tuần tự** trong một tiến trình, không có queue/song song.
- **Router là rule-based**: chưa có LLM planner (`planner: llm` chưa hỗ trợ, báo lỗi rõ).
- **Chưa có memory giữa các agent**: mỗi agent con chạy độc lập với input gốc.
- **MCP client khác** (Copilot, Claude Code) cùng dùng được qua 6 MCP tool trên; xem
  [`agent-integrations.md`](agent-integrations.md) mục 6 để biết file cần sinh.

---

## 8. Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`architecture.md`](architecture.md) | Kiến trúc phân lớp, luồng thực thi, bảo mật |
| [`kiro-integration.md`](kiro-integration.md) | Slash command, custom agent, hooks, MCP trong Kiro |
| [`agent-integrations.md`](agent-integrations.md) | Thêm tích hợp cho agent tool khác |
| [`uat-tutorial.md`](uat-tutorial.md) | Bộ test case nghiệm thu (gồm nhóm agent/orchestrator) |
| [`../skills/`](../skills/) | Skill của từng agent (team điền tiếp) |
