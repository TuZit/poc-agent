# Tích hợp agent tool (agent integrations)

**Trạng thái phase này: chỉ hỗ trợ Kiro.** Tài liệu này giải thích lớp tích hợp
hoạt động thế nào, và cách thêm một agent tool khác (Claude Code, GitHub Copilot,
Codex…) khi mở phase sau — **không cần sửa CLI, runtime hay packaging**.

---

## 1. Vì sao có lớp này

Các agent tool (Kiro, Claude Code, Copilot, Codex…) đều đọc file cấu hình trong
project, nhưng **mỗi tool một định dạng khác nhau**:

| Tool | File điều khiển chính | Đăng ký MCP |
|---|---|---|
| Kiro | `.kiro/steering/*.md` | `.kiro/settings/mcp.json` (`mcpServers`) |
| Claude Code | `CLAUDE.md` | `.mcp.json` (`mcpServers`) |
| GitHub Copilot | `.github/copilot-instructions.md` | `.vscode/mcp.json` (**`servers`**) |
| Codex CLI | `AGENTS.md` | `.codex/config.toml` (`[mcp_servers.<name>]`) |

Điểm chung: tất cả đều là **file trong project**, trỏ về cùng một MCP server
`agent-kit mcp serve`. Vì vậy chỉ cần một lớp "sinh file" dùng chung, không cần
nhân bản runtime.

---

## 2. CLI hiện có

```bash
# xem tool nào được hỗ trợ + đã cài chưa
agent-kit integration list

# cài (dùng được cả alias --ai cho tương thích tài liệu cũ)
agent-kit init my-project --integration kiro
agent-kit init my-project --ai kiro
agent-kit integration install kiro
agent-kit integration install all          # mọi integration đã đăng ký

# kiểm tra / gỡ
agent-kit integration status [kiro]        # exit 1 nếu còn file thiếu
agent-kit integration uninstall kiro --yes

# shorthand tương thích
agent-kit kiro install | status | uninstall
```

Nhiều integration cùng lúc: `--integration kiro,claude` hoặc lặp flag
`--ai kiro --ai claude`.

---

## 3. Kiến trúc: `TemplateIntegration`

```python
class TemplateIntegration:
    name: str                     # tên dùng trên CLI: "kiro"
    title: str                    # tên hiển thị: "Kiro"
    description: str              # mô tả cho `integration list`
    template_dir_name: str | None # thư mục trong integrations/ (mặc định = name)
    code_generated_files: tuple[str, ...]  # file sinh bằng code (không từ template)

    def destination_root(project_root) -> Path   # mặc định: project root
    def placeholders(project_root, command) -> dict[str, str]
    def template_files(project_root) -> list[Path]
    def managed_files(project_root) -> list[Path]     # template + code-generated
    def install(project_root, force, command) -> list[Path]
    def extra_files(project_root, force, command) -> list[Path]
    def status(project_root) -> IntegrationStatus
    def uninstall(project_root) -> list[Path]
```

Cơ chế:

- **Template** là file thật trong `integrations/<name>/`, được hatchling
  `force-include` vào wheel (`agent_kit/_bundled/integrations/...`) và vào binary
  PyInstaller → hoạt động cả khi đã cài.
- **Placeholder** trong template: `{{AGENT_KIT_COMMAND}}`, `{{PROJECT_NAME}}`,
  `{{PROJECT_ROOT}}`, `{{DEFAULT_INPUT}}`, `{{DEFAULT_OUTPUT}}`.
- **`destination_root()`**: Kiro trả về `<project>/.kiro` (mọi file nằm trong một
  thư mục); mặc định là project root cho các tool rải file khắp nơi.
- **Idempotent**: `install` bỏ qua file đã tồn tại (giữ bản người dùng sửa), chỉ ghi
  đè khi `--force`.
- **`managed_files()`** là nguồn sự thật duy nhất cho `status` và `uninstall` → chỉ
  xoá file do agent-kit tạo, giữ file của bạn.

Kiro dùng thêm `extra_files()` để sinh `.kiro/specs/agent-kit-poc/.config.kiro`
(spec id là UUID sinh mỗi lần cài, không thể là template tĩnh).

---

## 4. Thêm một agent tool mới (3 bước)

Ví dụ thêm tool tên `acme`:

**Bước 1 — thêm template**

```text
integrations/acme/
├── ACME.md                       # file instruction của tool
└── .acme/
    ├── mcp.json                  # đăng ký MCP server
    └── commands/run.md           # prompt/command file
```

Dùng placeholder cho lệnh:

```json
{ "mcpServers": { "agent-kit": { "command": "{{AGENT_KIT_COMMAND}}", "args": ["mcp", "serve"] } } }
```

**Bước 2 — thêm lớp integration**

```python
# src/agent_kit/integrations/acme.py
from agent_kit.integrations.base import TemplateIntegration


class AcmeIntegration(TemplateIntegration):
    name = "acme"
    title = "Acme Agent"
    description = "ACME.md + .acme/mcp.json MCP server"
    template_dir_name = "acme"


ACME = AcmeIntegration()
```

**Bước 3 — đăng ký**

```python
# src/agent_kit/integrations/__init__.py
INTEGRATION_REGISTRY: dict[str, TemplateIntegration] = {
    integration.name: integration for integration in (KIRO, ACME)
}
```

Xong. `agent-kit integration list|install|status|uninstall acme`,
`init --integration acme`, `--integration all` hoạt động ngay, không cần sửa
`cli/`, `mcp/`, `pyproject.toml` (thư mục `integrations/` đã được đóng gói sẵn)
hay `scripts/build-binary.sh`.

**Test tối thiểu** (theo mẫu `tests/unit/test_kiro_integration.py`):

1. cài vào project tạm → assert đúng danh sách file,
2. mọi file `.json`/`.toml` sinh ra phải parse được,
3. assert các key quan trọng (ví dụ `servers` vs `mcpServers`),
4. cài lần 2 không ghi đè file đã sửa; `--force` thì ghi đè,
5. `uninstall` chỉ xoá file do agent-kit tạo.

---

## 5. Nguyên tắc bắt buộc

1. **Chỉ ghi trong project.** Không ghi vào `$HOME`: cấu hình user-scope
   (`~/.claude.json`, `~/.codex/config.toml`, `~/.copilot/...`) là do người dùng
   quản lý. Ngoại lệ duy nhất nếu cần là một flag `--user` riêng, phải được thiết
   kế và test kỹ.
2. **Chỉ ghi file mà tool thật sự đọc.** Không sinh file "cho đủ bộ".
3. **Không commit file local.** Không sinh `CLAUDE.local.md`,
   `.claude/settings.local.json` vào repo.
4. **Idempotent + không phá file người dùng.** Mặc định không ghi đè.
5. **Không set key machine-local trong project scope.** Ví dụ Codex bỏ qua
   `model_provider`, `profiles`, `otel` trong `.codex/config.toml` → đừng set.
6. **Ghi nguồn tài liệu** trong docstring của module để lần sau còn kiểm chứng lại.

---

## 6. Tham chiếu định dạng cho các tool chưa triển khai

Các thông tin dưới đây **đã được kiểm chứng từ tài liệu chính thức** (độc lập,
chưa có code trong repo). Dùng làm điểm khởi đầu khi mở phase tích hợp tiếp theo.

### 6.1 Claude Code

| Việc | Đường dẫn project | Ghi chú |
|---|---|---|
| Project memory | `CLAUDE.md` (hoặc `.claude/CLAUDE.md`) | hỗ trợ `@path` import; `CLAUDE.md` che `AGENTS.md` |
| MCP server | `.mcp.json` ở **project root** | key `mcpServers`; có `type: stdio` |
| Bật MCP + quyền | `.claude/settings.json` | `enabledMcpjsonServers`, `permissions.allow/ask/deny` |
| Slash command | `.claude/commands/*.md` | frontmatter `description`, `argument-hint`, `allowed-tools`; thay `$ARGUMENTS` |
| Subagent | `.claude/agents/*.md` | frontmatter bắt buộc `name`, `description` |
| Hooks | `.claude/settings.json` | `hooks.<Event>[].matcher` + `hooks[].type: command` |

Nguồn: <https://code.claude.com/docs/en/memory>, <https://code.claude.com/docs/en/mcp>,
<https://code.claude.com/docs/en/skills>, <https://code.claude.com/docs/en/sub-agents>,
<https://code.claude.com/docs/en/settings>

### 6.2 GitHub Copilot (VS Code + coding agent)

| Việc | Đường dẫn project | Ghi chú |
|---|---|---|
| Instruction toàn repo | `.github/copilot-instructions.md` | luôn được nạp |
| Instruction theo path | `.github/instructions/*.instructions.md` | frontmatter `name`, `description`, `applyTo` (glob) |
| Prompt file | `.github/prompts/*.prompt.md` | frontmatter `description`, `agent`, `tools`, `${input:...}` |
| Custom agent | `.github/agents/*.agent.md` | `.chatmode.md` đã đổi tên thành `.agent.md` |
| MCP server | `.vscode/mcp.json` | key **`servers`** (không phải `mcpServers`) + `"type": "stdio"` |
| Instruction cho agent | `AGENTS.md` (bất kỳ đâu trong repo) | cũng dùng chung với Codex |

Nguồn: <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>,
<https://code.visualstudio.com/docs/agent-customization/custom-instructions>,
<https://code.visualstudio.com/docs/agent-customization/prompt-files>,
<https://code.visualstudio.com/docs/agent-customization/custom-agents>,
<https://code.visualstudio.com/docs/agent-customization/mcp-servers>

### 6.3 OpenAI Codex CLI

| Việc | Đường dẫn project | Ghi chú |
|---|---|---|
| Instruction | `AGENTS.md` (từ Git root xuống cwd) | `AGENTS.override.md` ưu tiên hơn; global ở `~/.codex/AGENTS.md` |
| MCP server | `.codex/config.toml` | `[mcp_servers.<name>]`; chỉ nạp cho project **trusted** |
| Timeout | trong cùng table | `startup_timeout_sec` (mặc định 10), `tool_timeout_sec` (mặc định 60) |
| Prompt | `~/.codex/prompts/*.md` | **chỉ user-scope**, và đã deprecated → ưu tiên `AGENTS.md` |

Key machine-local **không** được override từ project scope: `model_provider`,
`model_providers`, `openai_base_url`, `profiles`, `notify`, `otel`.

Nguồn: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>,
<https://learn.chatgpt.com/docs/extend/mcp>,
<https://learn.chatgpt.com/docs/config-file/config-reference>

---

## 7. Việc cần làm khi mở phase tích hợp đa tool

1. Chọn tool ưu tiên (theo thứ tự đề xuất: Claude Code → Copilot → Codex).
2. Thêm template + class + registry entry theo mục 4 (khoảng 30 phút/tool).
3. Thêm test theo mẫu ở mục 4 (bắt buộc — format các tool thay đổi theo thời gian).
4. Kiểm chứng thực tế: mở project bằng chính tool đó và xác nhận
   (a) tool thấy MCP server `agent-kit`, (b) gọi được `agent_kit_run_workflow`,
   (c) file instruction/prompt được nạp.
5. Cập nhật `docs/agent-integrations.md` (mục 1 + 6) và `README.md`.
6. Rebuild wheel + binary để template mới được đóng gói:
   `uv build && bash scripts/build-binary.sh`.

> ⚠️ Lưu ý chung: định dạng file của các tool này thay đổi khá nhanh (ví dụ VS Code
> đổi `.chatmode.md` → `.agent.md`; Codex deprecate custom prompts). Luôn kiểm chứng
> lại tài liệu trước khi implement và ghi nguồn vào docstring.

---

## 8. Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`kiro-integration.md`](kiro-integration.md) | Chi tiết integration đang dùng: Kiro |
| [`end-user-install.md`](end-user-install.md) | Cài đặt cho người dùng không cần Python |
| [`architecture.md`](architecture.md) | Kiến trúc tổng thể, extension seams |
| [`../integrations/kiro/`](../integrations/kiro/) | Template Kiro thực tế trong repo |
