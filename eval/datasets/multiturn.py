"""Bộ kịch bản hội thoại NHIỀU LƯỢT, kèm kiểm tra tính trung thực với nguồn.

Chạy: `.venv/Scripts/python.exe -m eval.datasets.multiturn`

Vì sao cần bộ này: ngày 2026-08-26 agent trả lời *"phí hủy chuyến Xanh SM Bike là
13.800 VNĐ"* trong khi đáp án đúng là 10.000đ — 13.800đ là **giá mở cửa**, không
phải phí huỷ. Lỗi lọt qua **toàn bộ** bộ đo cũ vì:

- `recall@3` chỉ hỏi "có lấy đúng file không", không hỏi "có trả lời đúng không";
- mọi câu trong golden set đều là câu **đơn lẻ**, không có lượt nối tiếp.

Mỗi kịch bản ở đây khai báo:
- `expect`      — con số/cụm từ BẮT BUỘC có trong câu trả lời cuối
- `forbid`      — con số gần giống nhưng SAI, chính là cái bẫy agent hay rơi vào
- `expect_source` — file tri thức phải được truy hồi ở lượt cuối
"""
from __future__ import annotations

# (id, mô tả, [các lượt], expect, forbid, expect_source)
MULTITURN_CASES: list[dict] = [
    {
        "id": "M001",
        "note": "Chính lỗi đã xảy ra thật: hỏi tiếp về loại xe khác",
        "turns": [
            "Phí hủy chuyến với xe taxi là bao nhiêu?",
            "Thế còn xe máy thì sao?",
        ],
        "expect": ["10.000"],
        "forbid": ["13.800"],  # giá mở cửa Bike, không phải phí huỷ
        "expect_source": "02_cancellation_and_fees.md",
    },
    {
        "id": "M002",
        "note": "Đại từ thay thế: 'cái đó' trỏ về phụ phí đêm",
        "turns": [
            "Phụ phí ban đêm áp dụng từ mấy giờ?",
            "Cái đó với xe máy là bao nhiêu tiền?",
        ],
        "expect": ["10.000"],
        "forbid": ["20.000"],  # mức của ô tô
        "expect_source": "01_pricing_and_surcharges.md",
    },
    {
        "id": "M003",
        "note": "Lượt sau rút gọn hoàn toàn, chỉ còn một từ",
        "turns": [
            "Phí phạt khách không xuất hiện với xe máy là bao nhiêu?",
            "Còn Luxury?",
        ],
        "expect": ["40.000"],
        "forbid": ["30.000", "15.000"],  # phí huỷ Luxury và no-show Bike
        "expect_source": "02_cancellation_and_fees.md",
    },
    {
        "id": "M004",
        "note": "Chuyển chủ đề rồi quay lại — bộ nhớ không được lẫn",
        "turns": [
            "Tôi có được mang thú cưng lên xe không?",
            "Hoàn tiền về thẻ tín dụng quốc tế mất bao lâu?",
        ],
        "expect": ["7", "14"],
        "forbid": ["3 – 5", "1 – 2"],  # thẻ nội địa và ví điện tử
        "expect_source": "03_refund_and_compensation.md",
    },
    {
        "id": "M005",
        "note": "Hỏi ngưỡng rồi hỏi hệ quả của ngưỡng",
        "turns": [
            "Số tiền hoàn tối đa mà hệ thống tự duyệt là bao nhiêu?",
            "Vượt mức đó thì sao?",
        ],
        # Chỉ bắt phần cốt lõi về NGHĨA. Bắt đủ nhiều từ khoá là biến phép đo
        # thành trò đoán chữ, và nó đã báo oan agent một lần vì thiếu chữ "duyệt".
        "expect": ["CSKH"],
        "forbid": [],
        "expect_source": "03_refund_and_compensation.md",
    },
    {
        "id": "M006",
        "note": "Ba lượt; lượt cuối cần nhớ cả đơn giá lẫn cửa sổ miễn phí 5 phút",
        "turns": [
            "Tôi muốn biết về phí chờ.",
            "Một tiếng bao nhiêu?",
            "Vậy nửa tiếng thì sao?",
        ],
        # KB mục 2.4: "Miễn phí 05 phút chờ đầu tiên". Nửa tiếng = 25 phút tính
        # phí = 25.000đ. Kỳ vọng ban đầu của bộ đo là 30.000đ — SAI, vì quên mất
        # cửa sổ miễn phí. Nay biến thành bẫy thật: agent nào bỏ qua 5 phút miễn
        # phí sẽ trả 30.000đ và bị bắt.
        "expect": ["25.000"],
        "forbid": ["30.000"],
        "expect_source": "01_pricing_and_surcharges.md",
    },
    {
        "id": "M007",
        "note": "Bẫy: cửa sổ huỷ miễn phí vs thời gian tài xế phải đợi",
        "turns": [
            "Tài xế phải đợi khách bao lâu trước khi được huỷ vì khách không xuất hiện?",
            "Còn tôi thì được huỷ miễn phí trong bao lâu?",
        ],
        "expect": ["02 phút", "2 phút"],
        # KHÔNG cấm "05 phút": KB mục 1.1 liệt kê "tài xế đứng yên quá 05 phút"
        # CŨNG là một điều kiện huỷ miễn phí, nên nhắc tới nó là đúng. Bẫy ban
        # đầu của bộ đo này sai, và nó đã báo oan agent một lần.
        "forbid": [],
        "expect_source": "02_cancellation_and_fees.md",
        "expect_any": True,  # "02 phút" hoặc "2 phút" đều đúng
    },
    {
        "id": "M008",
        "note": "Hỏi giá hai dòng xe liên tiếp, không được trộn số",
        "turns": [
            "Giá mở cửa 2km đầu của GreenCar tại Hà Nội là bao nhiêu?",
            "Của Bike thì sao?",
        ],
        "expect": ["13.800"],
        "forbid": ["30.500"],  # giá của GreenCar ở lượt trước
        "expect_source": "01_pricing_and_surcharges.md",
    },
]


def main() -> None:
    from collections import Counter

    turns = Counter(len(case["turns"]) for case in MULTITURN_CASES)
    print(f"  {len(MULTITURN_CASES)} kịch bản đa lượt")
    for count, n in sorted(turns.items()):
        print(f"    {count} lượt: {n} kịch bản")
    traps = sum(1 for case in MULTITURN_CASES if case["forbid"])
    print(f"  {traps} kịch bản có bẫy số liệu gần giống (forbid)")


if __name__ == "__main__":
    main()
