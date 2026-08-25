# Prompt BT5 — Generate ảnh workflow: infographic

> Mục đích: Render ảnh infographic workflow từ mã Mermaid.
> Dán vào: Codex / Nano Banana / Gemini (image generation).

```text
A professional, modern horizontal business process infographic diagram on a clean, light gray background (#F8FAFC). The design uses crisp technical line-art with subtle pastel color fills and a distinct isometric 3D perspective for icons.

LAYOUT & STRUCTURE:
- Visualize the provided Mermaidjs flowchart in a horizontal layout, strictly left to right.
- Segment the flow into stages separated by thin elegant vertical dividers.
- Connectors are thin, sharp dark gray arrows with smooth right-angle bends, precise directionality.

NODE STYLES & ILLUSTRATIONS (based on Mermaid source):
- Each node = a stylized rounded capsule (pastel palette) containing the node label in Vietnamese.
- Below/above each capsule, an isometric 3D illustration visualizes the step.
- AI steps (aiNode) use warm orange fill (#FFE0B2) with a small robot/AI icon.
- Human-in-the-loop steps (hitlNode) use soft red fill (#FFCDD2) with a person-review icon.
- Fallback steps use gray (#ECEFF1) with a warning/loop icon.
- Start/End nodes have distinct icons (clock/calendar for start, green check/flag for end).

BRANCHING:
- Decision diamonds branch correctly: "forward" for positive, "up/backwards" for negative flows, looping back when needed.

TYPOGRAPHY:
- All text in Vietnamese, exactly matching the Mermaid labels — no spelling errors.
- Modern sans-serif (Inter / Segoe UI / Roboto), high contrast, crisp 8k resolution.
- No overlapping elements, perfect alignment, plenty of white space.

OUTPUT: A high-resolution, sharp PNG file.

---

DƯỚI ĐÂY LÀ MÃ MERMAID CỦA TÔI — render thành infographic theo spec trên:

[DÁN MÃ MERMAID TỪ BT4]
```

> **Tip:** Nếu ảnh đầu ra bị lỗi font tiếng Việt (chữ có dấu vỡ), thêm vào đầu prompt: `"All Vietnamese diacritics must render correctly (ấ ầ ờ ư ơ ạ ụ)."` và yêu cầu AI generate lại.
>
> **Không có Codex/Nano Banana?** (Local-first / miễn phí) → dùng **Gemini free** sinh ảnh, HOẶC dùng **screenshot mermaid.live từ BT4** làm ảnh workflow (đã render đẹp, không cần tool trả phí).
