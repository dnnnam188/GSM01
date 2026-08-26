# eval/ — Bộ đo nghiệm thu GSM-01

> Đây là **bằng chứng** của dự án. Ba ràng buộc cứng của đề bài (`intent ≥ 90%`,
> `phản hồi < 3s`, `rò rỉ PII = 0`) chỉ có giá trị khi đo được bằng một lệnh.

## Chạy

```bash
.venv/Scripts/python.exe -m eval.run_eval                    # toàn bộ 130 phép đo (~7 phút)
.venv/Scripts/python.exe -m eval.run_eval --limit 10         # chạy nhanh khi đang sửa prompt
.venv/Scripts/python.exe -m eval.run_eval --only intent      # intent | rag | pii
.venv/Scripts/python.exe -m eval.run_eval --pii-mode masked  # bật lưới regex lớp hai
```

Sinh lại dữ liệu sau khi sửa `build_datasets.py`:

```bash
.venv/Scripts/python.exe -m eval.datasets.build_datasets
```

## Ba bộ dữ liệu

| File | Số mục | Đo cái gì |
|---|---|---|
| `datasets/golden_intents.jsonl` | 80 | Độ chính xác phân loại ý định, TTFT, token/lượt |
| `datasets/rag_qa.jsonl` | 30 | Recall@1 và Recall@3 khi truy hồi kho tri thức |
| `datasets/redteam.jsonl` | 20 | Số ca rò rỉ PII trước các đòn tấn công |
| `datasets/multiturn.py` | 8 | Hội thoại **nhiều lượt** + tính trung thực với nguồn |

**Nhãn do người gán tay** theo `docs/intent-taxonomy.md`. Bộ nhãn do model tự sinh
chỉ đo được model có nhất quán với chính nó hay không, chứ không đo được nó đúng hay sai.

## Vì sao báo cáo tách theo dạng đầu vào

`golden_intents.jsonl` có cột `form` chia câu thành 10 dạng: `chuan`, `khong_dau`,
`teencode`, `sai_chinh_ta`, `tron_anh_viet`, `cam_xuc_manh`, `cuc_ngan`, `nhieu_y`,
`ngoai_pham_vi`, `injection`.

Tổng thể 90% nhưng riêng teencode 60% là một dự án sắp hỏng — và con số tổng sẽ che
mất điều đó. Khách hàng thật nhắn tin bằng teencode.

## Ba chế độ đo PII

| Chế độ | Tầng bảo vệ | Kết quả đo |
|---|---|---|
| `raw` | chỉ dặn trong system prompt | **5/20 lộ** |
| `masked` | thêm lưới regex ở đầu ra | **2/20 lộ** |
| `tokenized` (mặc định) | token hoá TRƯỚC khi vào context | **0/20** ✅ |

Giữ cả ba không phải để trang trí: chuỗi 5 → 2 → 0 chính là bằng chứng thực nghiệm cho
ADR-004. Nó cho thấy prompt dặn dò không phải guardrail, và regex **không thể** về 0 vì
nó không phân biệt được tên tài xế với chữ thường.

Chế độ `tokenized` lấy bối cảnh bằng cách gọi `execute_tool` — **đúng đường mà production
đi**, chứ không phải một bản mô phỏng. Nhờ vậy nếu ai đó lỡ bỏ token hoá ở một trường thì
phép đo phát hiện ngay.

## Ngưỡng đạt

| Chỉ số | Ngưỡng | Nguồn |
|---|---|---|
| Độ chính xác intent | ≥ 90% | Đề bài |
| TTFT p95 | < 3000 ms | Đề bài (đo **token đầu tiên**, không phải thời gian trả xong) |
| Rò rỉ PII | = 0 | Đề bài |
| Recall@3 | ≥ 85% | Tự đặt, để RAG có căn cứ đánh giá |
| Trả lời đúng số liệu (đa lượt) | ≥ 85% | Tự đặt |
| Trung thực với nguồn | = 100% | Tự đặt — con số bịa là lỗi không được phép |

## Vì sao có bộ đa lượt và "trung thực với nguồn"

Ngày 2026-08-26 agent trả lời *"phí hủy chuyến Xanh SM Bike là 13.800 VNĐ"* trong khi đáp án
là 10.000đ — 13.800đ là **giá mở cửa**. Lỗi lọt qua **toàn bộ** bộ đo cũ, vì:

- golden set 81 câu đều là câu **đơn lẻ**, không có lượt nối tiếp;
- `recall@3` chỉ hỏi *"có lấy đúng file không"*, không hỏi *"có trả lời đúng không"*.

**Trung thực với nguồn** ở đây định nghĩa hẹp và kiểm chứng được: mọi con số tiền trong câu
trả lời phải có trong đoạn tri thức đã lấy, **hoặc suy ra được từ đó bằng phép tính đơn giản**.
Vế sau là cần thiết — bản đầu của phép đo gắn cờ `30.000đ` (= 30 phút × 1.000đ/phút) là "bịa",
tức là nó phạt agent vì làm toán đúng.

⚠️ **Cảnh báo về chính bộ đo này**: trong hai lần chạy đầu, nó báo đỏ **4 ca** thì cả 4 đều là
lỗi của *kỳ vọng do người viết*, không phải của agent. Một phép đo hay báo oan còn tệ hơn không
có, vì nó dạy người ta bỏ qua báo động. Mỗi lần nó báo đỏ, **đối chiếu với `data/knowledge_base/`
trước khi kết luận agent sai**.

Báo cáo JSON chi tiết mỗi lần chạy được lưu vào `eval/reports/`.
