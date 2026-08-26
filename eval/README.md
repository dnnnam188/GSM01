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

**Nhãn do người gán tay** theo `docs/intent-taxonomy.md`. Bộ nhãn do model tự sinh
chỉ đo được model có nhất quán với chính nó hay không, chứ không đo được nó đúng hay sai.

## Vì sao báo cáo tách theo dạng đầu vào

`golden_intents.jsonl` có cột `form` chia câu thành 10 dạng: `chuan`, `khong_dau`,
`teencode`, `sai_chinh_ta`, `tron_anh_viet`, `cam_xuc_manh`, `cuc_ngan`, `nhieu_y`,
`ngoai_pham_vi`, `injection`.

Tổng thể 90% nhưng riêng teencode 60% là một dự án sắp hỏng — và con số tổng sẽ che
mất điều đó. Khách hàng thật nhắn tin bằng teencode.

## Vì sao chế độ PII mặc định là `raw`

Chế độ `raw` đưa dữ liệu chuyến đi **có PII thật** thẳng vào context của LLM, không
token hoá. Đó là chủ ý: nó đo mức rò rỉ **khi chưa có tầng bảo vệ nào**, để con số
sau khi làm T-010 có cái mà so sánh.

Một bài test PII chạy trên context không hề chứa PII thì luôn cho kết quả 0 và không
chứng minh được điều gì.

## Ngưỡng đạt

| Chỉ số | Ngưỡng | Nguồn |
|---|---|---|
| Độ chính xác intent | ≥ 90% | Đề bài |
| TTFT p95 | < 3000 ms | Đề bài (đo **token đầu tiên**, không phải thời gian trả xong) |
| Rò rỉ PII | = 0 | Đề bài |
| Recall@3 | ≥ 85% | Tự đặt, để RAG có căn cứ đánh giá |

Báo cáo JSON chi tiết mỗi lần chạy được lưu vào `eval/reports/`.
