# Glossary (Từ Điển Thuật Ngữ Dự Án)

> 🎯 **Mục đích**: Giải nghĩa các thuật ngữ nghiệp vụ, tên viết tắt và quy ước riêng
> mà AI Agent **không thể tự suy ra** từ mã nguồn.

## 1. Thuật Ngữ Nghiệp Vụ

| Thuật ngữ | Ý nghĩa trong dự án này | Ghi chú |
|---|---|---|
| **Intent** | Một trong **đúng 10 nhãn** ý định đã khoá cứng ở `docs/intent-taxonomy.md` | Không được tự thêm nhãn mới |
| **Slot** | Thông tin bắt buộc phải có để gọi được tool (ví dụ `pickup`, `ride_id`) | Thiếu slot → agent hỏi lại, không đoán bừa |
| **Slot-filling** | Vòng hỏi lại khách cho tới khi đủ slot | |
| **HITL** | Human-in-the-loop — agent dừng giữa chừng chờ CSKH duyệt rồi **chạy tiếp** | Không phải "tạo ticket rồi kết thúc", xem ADR-003 |
| **Auto-refund** | Hoàn tiền agent được tự duyệt vì dưới ngưỡng trong `business_config` | Ngưỡng khởi điểm 50.000đ |
| **Ngưỡng HITL** | Số tiền vượt qua thì bắt buộc chuyển người duyệt | Là **dữ liệu**, không nằm trong prompt (ADR-006) |
| **Tool trace** | Chuỗi tool call của một hội thoại, hiển thị cho CSKH khi duyệt | Lấy từ bảng `tool_calls` |
| **Golden set** | Bộ câu hỏi tiếng Việt **đã gán nhãn tay**, dùng đo độ chính xác intent | 80 câu, xem T-008 |
| **Red-team set** | 20 prompt cố tình moi PII hoặc chèn chỉ dẫn độc hại | Thước đo của ADR-004 |
| **Auto-resolve rate** | Tỉ lệ yêu cầu agent xử lý trọn vẹn, không cần người | Mục tiêu ≥ 60% |
| **No-show** | Khách không xuất hiện tại điểm đón → có phí phạt | Xem `data/knowledge_base/02_*` |
| **Fraud score** | Điểm nghi ngờ gian lận của một yêu cầu hoàn tiền | Cao → ép sang HITL dù số tiền nhỏ |

## 2. Từ Viết Tắt

| Viết tắt | Đầy đủ | Ý nghĩa |
|---|---|---|
| **GSM-01** | Mã đề tài | Định danh dự án này |
| **CSKH** | Chăm sóc khách hàng | Vai trò `agent` trong hệ thống |
| **HITL** | Human-in-the-loop | Xem mục 1 |
| **PII** | Personally Identifiable Information | SĐT, họ tên, điểm đón/đến |
| **RAG** | Retrieval-Augmented Generation | Truy hồi kho tri thức trước khi trả lời |
| **TTFT** | Time To First Token | **Chỉ số đo ngưỡng "< 3s"** của đề bài |
| **ADR** | Architecture Decision Record | `.ai/context/decisions.md` |
| **DoD** | Definition of Done | `.ai/rules/definition-of-done.md` |
| **CSAT** | Customer Satisfaction | Điểm hài lòng 1–5 cuối phiên |

## 3. Quy Ước Đặt Tên Riêng Của Dự Án

| Mẫu | Ý nghĩa | Ví dụ |
|---|---|---|
| `<PHONE_xx>`, `<ADDR_xx>` | Placeholder PII đưa vào context LLM thay cho dữ liệu thật | `<PHONE_C7>` |
| `booking.*`, `complaint.*` | Tiền tố nhóm intent | `booking.cancel` |
| `T-0xx` | ID task trong `.ai/TASKS.md`, không tái sử dụng | `T-007` |
| `F0x` | ID tính năng trong `docs/PRD.md` | `F11` = HITL hoàn tiền |
| `ADR-00x` | ID quyết định kiến trúc | `ADR-004` = token hoá PII |
| `D1`…`D13` | Ngày thứ mấy của sprint 13 ngày | D3 = 27/08/2026 |

## 4. Cảnh Báo Dễ Nhầm Lẫn

| Dễ nhầm | Thực ra là |
|---|---|
| "Độ trễ < 3s" | Đo bằng **TTFT** (token đầu tiên), **không phải** thời gian trả lời xong |
| `booking.cancel` | Khác `refund.request`: có đòi tiền → luôn là `refund.request` |
| `fare.inquiry` | Khác `policy.faq`: hỏi **con số tiền** → `fare.inquiry`; hỏi **điều kiện/quy trình** → `policy.faq` |
| `trip.lookup` | Khác `fare.inquiry`: chuyến **đã tồn tại trong DB** → `trip.lookup` |
| Che PII | Không phải lọc regex đầu ra, mà là **token hoá trước khi vào LLM** (ADR-004) |
| "Agent" | Trong code là **vai trò nhân viên CSKH** (`role='agent'`), không phải AI Agent |
