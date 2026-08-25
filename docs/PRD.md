# PRD — GSM-01: AI Agent CSKH Đặt Xe & Xử Lý Khiếu Nại (Xanh SM)

- **Phiên bản**: v1.0 · **Ngày chốt**: 2026-08-25 · **Trạng thái**: `Đã đóng băng cho Sprint 13 ngày`
- **Nguyên tắc**: mọi thay đổi phạm vi sau ngày này phải ghi ADR mới, không sửa trực tiếp file này.

---

## 1. Tóm Tắt Sản Phẩm

- **Tên sản phẩm**: GSM-01 — Trợ lý CSKH đa vai trò cho dịch vụ gọi xe Xanh SM.
- **Vấn đề**: Tổng đài nhận hàng nghìn yêu cầu/ngày (đặt xe, hỏi cước, đổi điểm đến, khiếu nại tài xế,
  thất lạc đồ, đòi hoàn tiền). Nhân viên phải tra cứu thủ công lịch sử chuyến và chính sách hoàn tiền
  → phản hồi chậm, dễ sai sót, chi phí nhân sự cao.
- **Giải pháp**: Một AI Agent có khả năng lập kế hoạch nhiều bước (LangGraph), phân loại ý định,
  truy vấn dữ liệu chuyến đi thật, tra cứu chính sách bằng RAG, gọi tool nghiệp vụ
  (đặt/hủy/hoàn tiền/tạo ticket), và **dừng lại xin phê duyệt của con người** khi vượt ngưỡng rủi ro.
- **Giá trị đo được**: mục tiêu tự động xử lý trọn vẹn ≥ 60% yêu cầu (auto-resolve rate),
  thời gian phản hồi đầu tiên < 3 giây thay vì hàng phút chờ tổng đài.

---

## 2. Chân Dung Người Dùng

### P1 — Khách hàng (vai trò `customer`)
- **Bối cảnh**: dùng điện thoại, đang vội hoặc đang bực. Nhắn tiếng Việt không dấu, viết tắt, sai chính tả.
- **Mục tiêu**: được trả lời ngay, không phải kể lại thông tin đã có trong hệ thống, không phải chờ tổng đài.
- **Nỗi đau**: phải đọc mã chuyến dài, phải lặp lại câu chuyện cho từng nhân viên.

### P2 — Nhân viên CSKH (vai trò `agent`)
- **Bối cảnh**: xử lý song song nhiều ca, cần quyết định nhanh dựa trên bằng chứng.
- **Mục tiêu**: chỉ can thiệp vào ca thật sự cần người; khi can thiệp phải thấy ngay
  toàn bộ hội thoại, dữ liệu chuyến và **đề xuất kèm lý do của AI**.
- **Nỗi đau**: duyệt mù, không biết AI dựa vào đâu; không truy vết được ai đã duyệt cái gì.

---

## 3. Yêu Cầu Tính Năng

> `P0` = bắt buộc để nghiệm thu · `P1` = hạng mục nâng cao của đề bài · `P2` = làm nếu còn thời gian.

| ID | Tính năng | Ưu tiên | Mô tả | Tiêu chí nghiệm thu (kiểm chứng được) |
|---|---|---|---|---|
| F01 | Đăng nhập 2 vai trò | P0 | JWT, phân quyền `customer` / `agent` | Đăng nhập trả về JWT chứa `role`; `customer` gọi API dashboard → HTTP 403 |
| F02 | Chat streaming | P0 | WebSocket, token hiện dần | Token đầu tiên xuất hiện < 3s (đo p95 trên 50 lượt) |
| F03 | Phân loại intent | P0 | 10 nhãn theo `docs/intent-taxonomy.md` | `eval/run_eval.py` báo accuracy ≥ 90% trên golden set 80 câu |
| F04 | Trả lời từ RAG | P0 | Truy hồi từ 7 file `data/knowledge_base/` | Câu trả lời chính sách kèm trích dẫn tên file nguồn; recall@3 ≥ 85% |
| F05 | Truy vấn dữ liệu chuyến | P0 | Tool `get_ride_history`, `get_ride_detail` | Hỏi "chuyến hôm qua hết bao nhiêu" → trả đúng số tiền trong DB |
| F06 | Đặt xe giả lập | P0 | Tool `book_ride` có slot-filling | Thiếu điểm đón → agent hỏi lại; đủ slot → tạo bản ghi `rides` mới |
| F07 | Hủy chuyến | P0 | Tool `cancel_ride`, tính phí hủy theo chính sách | Hủy trong 2 phút → phí 0đ; sau đó → đúng mức phí trong KB |
| F08 | Tạo ticket khiếu nại | P0 | Tool `create_ticket` cho khiếu nại tài xế / thất lạc đồ | Ticket được ghi vào DB, trả mã cho khách, hiện trên dashboard CSKH |
| F09 | Memory hội thoại | P0 | Buffer N lượt + tóm tắt cuộn + hồ sơ khách | Sang lượt thứ 12 vẫn nhớ mã chuyến đã nhắc ở lượt 2 |
| F10 | Log tool calls | P0 | Bảng `tool_calls` ghi input/output/latency/lỗi | Mỗi lần gọi tool sinh đúng 1 dòng; xem được trên dashboard |
| F11 | **HITL duyệt hoàn tiền** | P1 | Hoàn tiền > 50.000đ → graph dừng, chờ CSKH | CSKH bấm Duyệt → hội thoại của khách **tự chạy tiếp** và báo kết quả |
| F12 | Dashboard CSKH | P1 | Hàng đợi HITL + transcript + tool trace + nút Duyệt/Từ chối | Từ chối bắt buộc nhập lý do; ghi vào `audit_log` |
| F13 | Dashboard thống kê | P1 | Ticket theo intent, CSAT, auto-resolve rate, chi phí token | 4 chỉ số + 2 biểu đồ, số liệu khớp DB |
| F14 | Cảnh báo hạn mức | P1 | Vượt ngưỡng hoàn tiền/ngày hoặc token/ngày → cảnh báo | Bơm dữ liệu vượt ngưỡng → banner đỏ hiện trên dashboard |
| F15 | Guardrail PII + fallback | P1 | PII token hóa trước khi vào LLM; tool lỗi → trả lời an toàn | Bộ red-team 20 prompt → 0 lần lộ SĐT/địa chỉ đầy đủ; tắt DB → agent xin lỗi, không văng stacktrace |
| F16 | Thu thập CSAT | P2 | Cuối phiên hỏi mức hài lòng 1–5 | Điểm được ghi vào bảng `csat` |

---

## 4. Yêu Cầu Phi Chức Năng (ràng buộc cứng của đề bài)

| Chỉ số | Ngưỡng | Cách đo |
|---|---|---|
| Độ chính xác intent | **≥ 90%** | `eval/run_eval.py` trên golden set có nhãn |
| Độ trễ phản hồi | **< 3s** | p95 **TTFT** (time-to-first-token) qua WebSocket |
| Rò rỉ PII | **= 0** | Bộ red-team 20 prompt; đếm số lần SĐT/địa chỉ đầy đủ lọt ra ngoài |
| Chi phí token | Có trần & cảnh báo | Ghi `prompt_tokens`/`completion_tokens` mỗi lượt vào DB |
| HITL | Bắt buộc | Hoàn tiền > 50.000đ hoặc khiếu nại mức nghiêm trọng → không được tự duyệt |

---

## 5. Ngoài Phạm Vi (cố ý KHÔNG làm trong 13 ngày)

Ghi rõ để agent phiên sau không "cải tiến" ngược:

- Đăng ký tài khoản, quên mật khẩu, OTP → dùng tài khoản seed sẵn.
- Thanh toán thật, bản đồ thật, tính quãng đường thật → mô phỏng bằng dữ liệu seed.
- Ứng dụng di động, thông báo đẩy.
- Đa ngôn ngữ (chỉ tiếng Việt).
- Fine-tune model, CI/CD tự động, load test quy mô lớn.

---

## 6. Điều Kiện Nghiệm Thu Toàn Dự Án

Coi là "xong" khi và chỉ khi cả 5 điều sau đúng cùng lúc:

1. Web chạy online (FE trên Vercel, BE trên Render), đăng nhập được cả 2 vai trò.
2. `eval/run_eval.py` chạy ra bảng số, intent ≥ 90%, PII leak = 0.
3. Demo được trọn kịch bản HITL: khách đòi hoàn 120.000đ → agent dừng → CSKH duyệt → khách nhận thông báo.
4. Dashboard CSKH hiển thị đúng tool trace của hội thoại vừa diễn ra.
5. `.ai/TASKS.md` và `.ai/JOURNAL.md` phản ánh đúng trạng thái thật.
