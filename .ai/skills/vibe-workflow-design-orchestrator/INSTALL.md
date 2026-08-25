# Cài đặt vibe-workflow-design-orchestrator

## Skill này làm gì

Sinh trọn vẹn một **Workflow Design Package** (chuẩn "Workflow Mindset") cho một use-case doanh nghiệp:
đi từ "tôi muốn tự động hoá quy trình X" tới một gói tài liệu sẵn sàng trình lãnh đạo —
as-is → ESIA to-be → hardening production → sơ đồ Mermaid → ảnh infographic → deck tham mưu 30 ngày,
ráp lại thành 1 Workflow Design Doc 7 phần.

## Yêu cầu

- Python 3.9+ (cho các script validator / anonymizer / review_queue)
- Một client đọc được `SKILL.md`:
  - **Claude Code** (CLI / desktop / web)
  - **Antigravity** (Google)
  - **ChatGPT Desktop** + các client tương tự (dùng SKILL.md như system/agent instruction)
- KHÔNG cần API key hay MCP server riêng.

## Cài đặt

### Claude Code (personal — áp dụng mọi project)

```bash
unzip vibe-workflow-design-orchestrator.zip -d ~/.claude/skills/
```

### Claude Code (chỉ cho 1 project)

```bash
unzip vibe-workflow-design-orchestrator.zip -d .claude/skills/
```

### Antigravity / ChatGPT Desktop / client khác

Giải nén thư mục, mở file `SKILL.md`, dán toàn bộ nội dung vào ô **System instruction /
Agent instruction / Custom prompt** của agent. Các file trong `prompt/`, `synthetic-data/`,
`output/templates/` được tham chiếu tương đối — giữ nguyên cấu trúc thư mục khi tham chiếu.

## Cài hooks (tuỳ chọn, Claude Code)

Hooks tự validate output mỗi khi Write/Edit:

```bash
bash ~/.claude/skills/vibe-workflow-design-orchestrator/script/install_hooks.sh
```

## Xác nhận cài đặt

Khởi động lại Claude Code, rồi gõ:

```
/vibe-workflow-design-orchestrator
```

## Gỡ cài đặt

```bash
rm -rf ~/.claude/skills/vibe-workflow-design-orchestrator
```

## Dependencies (external — KHÔNG bắt buộc để chạy)

Skill tự đứng được. Các skill sau chỉ cần khi muốn nối tiếp pipeline:

| Skill | Khi nào cần |
|-------|-------------|
| `vibe-score-workflow-design` | Chấm/thẩm định package đã sinh |
| `vibe-aiworkforce` | Build AI workforce thực sự execute workflow |
| `vibe-slide-orchestrator` | Render deck PPTX thật từ W6 |
