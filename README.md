# Tên Dự Án (Project Name)

> 🚀 *Một đoạn giới thiệu ngắn gọn, ấn tượng về mục đích và giá trị của dự án.*

---

## 📖 Mục Lục
1. [Giới Thiệu](#-giới-thiệu)
2. [Tính Năng Chính](#-tính-năng-chính)
3. [Công Nghệ Sử Dụng](#-công-nghệ-sử-dụng)
4. [Hướng Dẫn Cài Đặt (Windows)](#-hướng-dẫn-cài-đặt-windows)
5. [Cấu Trúc Thư Mục](#-cấu-trúc-thư-mục)
6. [Hệ Thống AI Agent](#-hệ-thống-ai-agent)
7. [Tài Liệu Chi Tiết](#-tài-liệu-chi-tiết)

---

## 🌟 Giới Thiệu
Mô tả chi tiết bài toán dự án giải quyết và đối tượng người dùng hướng đến.

---

## ⚡ Tính Năng Chính
- **Tính năng 1**: Mô tả ngắn gọn tính năng 1.
- **Tính năng 2**: Mô tả ngắn gọn tính năng 2.
- **Tính năng 3**: Mô tả ngắn gọn tính năng 3.

---

## 🛠️ Công Nghệ Sử Dụng
- **Ngôn ngữ**: TypeScript / JavaScript / Python
- **Framework**: [Tên Framework]
- **Styling**: [Tên UI Library]
- **Database**: [Tên Database]

---

## 💻 Hướng Dẫn Cài Đặt (Windows)

### 1. Yêu cầu hệ thống
- Node.js (v20+) hoặc Python (3.11+)
- Git for Windows

### 2. Các bước cài đặt
```powershell
# 1. Clone repository
git clone <repository-url>
cd "Side Project"

# 2. Cài đặt dependencies (ví dụ với npm)
npm install

# 3. Thiết lập biến môi trường
Copy-Item .env.example .env

# 4. Chạy môi trường phát triển (Dev server)
npm run dev
```

---

## 📂 Cấu Trúc Thư Mục
```text
Side Project/
├── .ai/                          # Trung tâm tri thức & quy trình dành cho AI Agent
│   ├── JOURNAL.md                # Nhật ký bàn giao ca — "ĐÃ xảy ra chuyện gì?"
│   ├── TASKS.md                  # Bảng công việc — "CÒN phải làm gì?"
│   ├── context/                  # Hiểu dự án
│   │   ├── project-overview.md   #   Dự án này là gì?
│   │   ├── architecture.md       #   Hệ thống vận hành ra sao?
│   │   ├── codemap.md            #   Muốn sửa X thì mở file nào?
│   │   ├── decisions.md          #   Vì sao chọn cách làm này? (ADR)
│   │   ├── glossary.md           #   Thuật ngữ dự án nghĩa là gì?
│   │   └── bug-history.md        #   Lỗi này từng gặp chưa?
│   ├── rules/                    # Quy tắc bắt buộc tuân thủ
│   │   ├── coding-style.md       #   Phong cách lập trình
│   │   ├── environment.md        #   Môi trường Windows & thực thi lệnh
│   │   ├── security.md           #   Bảo mật & biến môi trường
│   │   └── definition-of-done.md #   Thế nào mới được gọi là "xong"
│   ├── skills/                   # Quy trình kích hoạt theo nhu cầu
│   │   ├── git-workflow.md       #   Git, commit, branch
│   │   ├── testing.md            #   Kiểm thử & quy trình sửa bug 4 bước
│   │   └── ui-ux-guide.md        #   Tiêu chuẩn giao diện
│   └── templates/                # Mẫu ghi chép chuẩn hóa
│       ├── journal-entry.md      #   Mẫu entry nhật ký
│       ├── task.md               #   Mẫu task
│       └── adr.md                #   Mẫu quyết định kiến trúc
├── docs/
│   ├── PRD.md                    # Đặc tả yêu cầu sản phẩm
│   └── API.md                    # Đặc tả API & dữ liệu
├── src/                          # Mã nguồn chính
├── tests/                        # Kiểm thử tự động
├── index.html                    # Ứng dụng trang tĩnh (điểm chạy hiện tại)
├── AGENTS.md                     # ⭐ NGUỒN CHÂN LÝ cho mọi AI Agent
├── CLAUDE.md                     # Con trỏ cho Claude Code → AGENTS.md
├── GEMINI.md                     # Con trỏ cho Antigravity / Gemini → AGENTS.md
├── .cursorrules                  # Con trỏ cho Cursor IDE → AGENTS.md
└── .windsurfrules                # Con trỏ cho Windsurf IDE → AGENTS.md
```

---

## 🤖 Hệ Thống AI Agent

Dự án chuẩn hóa cho quy trình làm việc đa Agent (Claude Code, Antigravity/Gemini, Cursor, Codex, Windsurf).

**Nguồn chân lý duy nhất là `AGENTS.md`** — bốn file `CLAUDE.md`, `GEMINI.md`, `.cursorrules`,
`.windsurfrules` chỉ là con trỏ dẫn về đó. Muốn đổi quy tắc, **chỉ sửa `AGENTS.md`**.

### Vòng lặp bàn giao giữa các phiên
```text
MỞ PHIÊN    →  .ai/JOURNAL.md      (3–5 entry gần nhất: chuyện gì vừa xảy ra)
            →  .ai/TASKS.md ⏳     (cầm tiếp việc đang dở)
            →  .ai/context/codemap.md  (muốn sửa X thì mở file nào)

TRONG PHIÊN →  đổi trạng thái task ☐ → ⏳ ngay khi bắt đầu

ĐÓNG PHIÊN  →  .ai/rules/definition-of-done.md  (đủ điều kiện mới được gọi là xong)
            →  cập nhật .ai/TASKS.md
            →  ghi 1 entry .ai/JOURNAL.md
```

Nhờ vòng lặp này, bất kỳ Agent nào mở dự án lên cũng biết ngay dự án đang ở đâu và làm tiếp việc gì.

---

## 📚 Tài Liệu Chi Tiết

**Dành cho AI Agent**
- [⭐ Hướng dẫn & điều phối Agent (AGENTS.md)](AGENTS.md)
- [Bảng công việc — còn phải làm gì](.ai/TASKS.md)
- [Nhật ký bàn giao ca](.ai/JOURNAL.md)
- [Tổng quan dự án](.ai/context/project-overview.md)
- [Kiến trúc hệ thống](.ai/context/architecture.md)
- [Bản đồ mã nguồn](.ai/context/codemap.md)
- [Nhật ký quyết định kiến trúc (ADR)](.ai/context/decisions.md)
- [Tiêu chuẩn hoàn thành](.ai/rules/definition-of-done.md)

**Dành cho người phát triển**
- [Bản đặc tả yêu cầu sản phẩm (PRD)](docs/PRD.md)
- [Đặc tả API & Dữ liệu](docs/API.md)
