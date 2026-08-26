# Bug History & Troubleshooting Log

> 💡 *Mục đích: Ghi lại các lỗi oái oăm hoặc các vấn đề kỹ thuật đặc thù đã giải quyết thành công để các AI Agent không bao giờ lặp lại lỗi tương tự.*

## Mẫu Ghi Lỗi (Template)

### [YYYY-MM-DD] - Tên lỗi ngắn gọn
- **Hiện tượng**: Mô tả lỗi xảy ra như thế nào, mã lỗi (nếu có).
- **Nguyên nhân cốt lõi**: Giải thích lý do gây ra lỗi.
- **Giải pháp xử lý**: Cách đã sửa và tệp đã thay đổi.
- **Lưu ý phòng ngừa**: Điều cần tránh trong tương lai.

---

## Danh Sách Lỗi Đã Xử Lý

### [2026-08-26] - `thinkingBudget` sai tham số làm chết toàn bộ lời gọi LLM, không test nào bắt được
- **Hiện tượng**: Mọi lời gọi Gemini trả `400 INVALID_ARGUMENT`. Agent chỉ còn trả câu xin lỗi.
  Lời gọi trần (không schema, không system) thì chạy, nên ban đầu nghi oan cho `responseSchema`.
- **Chẩn đoán sai lúc đầu**: Chạy 15 lần một request y hệt cho ra 10 lần 400 + 5 lần 429, nên
  tôi kết luận "Gemini báo cạn hạn mức bằng cả 400 lẫn 429" và đã sửa code coi 400 là tín hiệu
  hết hạn mức. **Kết luận đó sai.** Các lần 429 là quota thật, còn các lần 400 đến từ nguyên
  nhân khác hẳn — và việc trộn hai thứ suýt nữa che mất lỗi thật.
- **Nguyên nhân cốt lõi**: `_gemini_body` có `"thinkingConfig": {"thinkingBudget": 0}`.
  Model `gemini-3.5-flash-lite` **không nhận** `thinkingBudget`. Đo đối chứng:
  không có `thinkingConfig` → 8/8 thành công · `thinkingBudget: 0` → **8/8 lỗi 400** ·
  `thinkingLevel: "low"` → 8/8 thành công.
- **Giải pháp xử lý**: Đổi sang `thinkingLevel: "low"` trong `src/backend/llm/client.py`.
  Hoàn nguyên thay đổi coi 400 là hết hạn mức — 400 nghĩa là request sai, và rơi sang provider
  dự phòng khi gặp 400 chỉ làm lỗi cấu hình bị giấu đi.
- **Lưu ý phòng ngừa**:
  1. **Cơ chế xuống cấp êm đã giấu lỗi.** Toàn bộ test khác hoặc không gọi model, hoặc coi lỗi
     model là chuyện bình thường rồi trả câu xin lỗi — nên 100% lời gọi hỏng mà mọi test vẫn xanh.
     Đã thêm `tests/test_llm_config.py` gọi API thật đúng một lần với chính body của production,
     cộng một kiểm tra tĩnh chặn `thinkingBudget`.
  2. Khi thấy lỗi lạ, **đối chứng có/không từng tham số** trước khi kết luận về hạ tầng.
  3. Đừng suy ra nguyên nhân từ tỉ lệ lỗi. 10/15 lần 400 trông rất giống giới hạn hệ thống,
     nhưng thực ra là 100% các lời gọi đi qua đúng một đoạn code sai.


### [2026-08-26] - RAG đa lượt trả lời sai số liệu vì truy hồi bằng câu hỏi thô
- **Hiện tượng**: Lượt 1 khách hỏi "Phí hủy chuyến với xe taxi là bao nhiêu?" → trả lời đúng
  20.000đ. Lượt 2 khách hỏi tiếp "Thế còn xe máy thì sao?" → agent trả lời **"phí hủy chuyến
  Xanh SM Bike là 13.800 VNĐ"**. Sai: 13.800đ là **giá mở cửa 2km đầu**, phí hủy Bike là 10.000đ.
- **Nguyên nhân cốt lõi**: Câu hỏi nối tiếp "Thế còn xe máy thì sao?" được đem đi truy hồi
  **nguyên văn**. Câu này không mang ngữ cảnh "phí hủy", nên vector gần nhất rơi vào
  `01_pricing_and_surcharges.md` (bảng giá) thay vì `02_cancellation_and_fees.md`. Model nhận
  được cả hai file trong context và lấy nhầm con số. Đây là lỗi kinh điển của RAG nhiều lượt:
  **truy hồi thì không có bộ nhớ, chỉ có câu chữ**.
- **Giải pháp xử lý**: Thêm trường `standalone_query` vào structured output của router
  (`src/backend/agent/router.py`) — model viết lại tin nhắn thành câu hỏi tự đứng được, có đủ
  ngữ cảnh. `pipeline.py` truy hồi bằng câu đã viết lại thay vì tin nhắn thô.
  Gộp vào **cùng một lần gọi LLM** đang có, nên không tốn thêm độ trễ nào.
  Kiểm chứng lại: câu viết lại thành "Phí hủy chuyến với dịch vụ xe máy của Xanh SM là bao
  nhiêu tiền?", nguồn truy hồi đúng `02_cancellation_and_fees.md`, trả lời đúng 10.000đ.
- **Lưu ý phòng ngừa**:
  1. **Recall@3 = 100% không có nghĩa là câu trả lời đúng.** Bộ eval hiện chỉ đo *truy hồi
     đúng file hay không* trên câu hỏi đơn lẻ, không đo *câu trả lời có trung thực với nguồn
     hay không*, và hoàn toàn không đo hội thoại nhiều lượt. Lỗi này lọt qua toàn bộ eval.
  2. **ĐÃ LÀM ở T-012**: bộ eval đa lượt (8 kịch bản) + chỉ số trung thực với nguồn.
     Kịch bản `M001` tái hiện đúng lỗi này và nay đạt — tức đã có lưới chặn hồi quy.
  3. Mọi tính năng RAG mới phải tự hỏi: "câu này đem đi tra thẳng có đủ nghĩa không?"

### [Ví Dụ] [2026-08-24] - Lỗi đường dẫn Windows khi chạy script PowerShell
- **Hiện tượng**: Lệnh shell báo lỗi không tìm thấy đường dẫn có chứa dấu cách `Side Project`.
- **Nguyên nhân**: Quên bọc đường dẫn trong dấu ngoặc kép khi truyền tham số trên PowerShell.
- **Giải pháp**: Luôn sử dụng `"$Path"` hoặc dấu nháy kép `"` cho mọi đường dẫn tệp.
- **Lưu ý phòng ngừa**: Luôn kiểm tra tính tương thích của shell Windows trong `.ai/rules/environment.md`.
