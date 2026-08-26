"""Token hoá PII (T-010, ADR-004).

Đo được ở D3 trước khi có tầng này: chỉ dặn trong system prompt lộ **5/20**,
thêm lưới regex còn **2/20**, và regex không thể về 0 vì nó không phân biệt được
tên tài xế với chữ thường.

Các test ở đây khoá chặt tính chất khiến tầng này khác hẳn lọc regex: nó thay
**theo trường đã biết là PII**, chứ không đoán theo mẫu.
"""
from __future__ import annotations

from datetime import UTC, datetime

from src.backend.pii.tokenizer import PLACEHOLDER_RE, PiiVault, tokenize_model
from src.backend.tools.contracts import GetRideDetailOutput, GetRideHistoryOutput, RideSummary


def _ride(**kwargs) -> RideSummary:
    base = dict(ride_code="XSM-DETOUR-01", service_type="GREENCAR", status="COMPLETED",
                pickup_address="12 Nguyễn Trãi, Thanh Xuân, Hà Nội",
                dropoff_address="45 Kim Mã, Ba Đình, Hà Nội",
                final_fare=130_000, requested_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC))
    base.update(kwargs)
    return RideSummary(**base)


def test_moi_truong_pii_deu_bi_thay_con_du_lieu_nghiep_vu_thi_khong():
    vault = PiiVault(conversation_id="c1")
    out = tokenize_model(_ride(), vault)
    assert PLACEHOLDER_RE.fullmatch(out.pickup_address)
    assert PLACEHOLDER_RE.fullmatch(out.dropoff_address)
    # Những thứ agent cần để làm việc thì phải giữ nguyên
    assert out.ride_code == "XSM-DETOUR-01"
    assert out.final_fare == 130_000
    assert out.service_type == "GREENCAR"


def test_cung_gia_tri_cho_cung_placeholder_trong_mot_hoi_thoai():
    """Nhờ vậy LLM vẫn suy luận được 'hai chuyến cùng một tài xế' mà không biết là ai."""
    vault = PiiVault(conversation_id="c1")
    a = tokenize_model(_ride(ride_code="XSM-AAA01"), vault)
    b = tokenize_model(_ride(ride_code="XSM-BBB02"), vault)
    assert a.pickup_address == b.pickup_address
    assert a.pickup_address != a.dropoff_address


def test_hai_hoi_thoai_khac_nhau_cho_placeholder_khac_nhau():
    """Không để lộ mối liên hệ giữa các hội thoại của những khách khác nhau."""
    v1, v2 = PiiVault(conversation_id="c1"), PiiVault(conversation_id="c2")
    assert (tokenize_model(_ride(), v1).pickup_address
            != tokenize_model(_ride(), v2).pickup_address)


def test_dam_bao_xuong_ca_model_long_nhau_va_danh_sach():
    """`GetRideHistoryOutput` chứa danh sách chuyến — bỏ sót là lộ toàn bộ lịch sử."""
    vault = PiiVault(conversation_id="c1")
    history = GetRideHistoryOutput(rides=[_ride(ride_code="XSM-AAA01"), _ride(ride_code="XSM-BBB02")],
                                   total_found=2)
    out = tokenize_model(history, vault)
    for ride in out.rides:
        assert PLACEHOLDER_RE.fullmatch(ride.pickup_address)
        assert PLACEHOLDER_RE.fullmatch(ride.dropoff_address)


def test_khoi_phuc_duoc_gia_tri_that_cho_vai_tro_co_quyen():
    vault = PiiVault(conversation_id="c1")
    out = tokenize_model(_ride(), vault)
    assert vault.detokenize(out.pickup_address) == "12 Nguyễn Trãi, Thanh Xuân, Hà Nội"


def test_che_hien_thi_khong_lo_gia_tri_va_khong_lo_ca_co_che():
    vault = PiiVault(conversation_id="c1")
    phone = vault.placeholder_for("0912345678", "PHONE")
    name = vault.placeholder_for("Ngô Đức Thắng", "NAME")
    masked = vault.mask_for_display(f"Tài xế {name}, số {phone}")
    assert "0912345678" not in masked
    assert "Ngô Đức Thắng" not in masked
    # Không để lộ luôn cả placeholder ra cho khách
    assert "<PHONE" not in masked and "<NAME" not in masked
    assert "0912****78" in masked and "Ngô ***" in masked


def test_quet_ca_van_ban_tu_do_chua_gia_tri_da_biet():
    """PII còn lẫn trong mô tả khiếu nại do chính khách nhập."""
    vault = PiiVault(conversation_id="c1")
    vault.placeholder_for("0912345678", "PHONE")
    cleaned = vault.tokenize_text("Anh gọi giúp em số 0912345678 nhé")
    assert "0912345678" not in cleaned
    assert PLACEHOLDER_RE.search(cleaned)


def test_khong_bo_sot_truong_pii_nao_cua_get_ride_detail():
    """Chặn hồi quy: thêm trường PII mới vào contract mà quên là lộ ngay."""
    from src.backend.tools.contracts import pii_fields_of

    vault = PiiVault(conversation_id="c1")
    detail = GetRideDetailOutput(
        ride_code="XSM-LOSTITEM-01", service_type="GREENCAR", status="COMPLETED",
        pickup_address="1 Trần Duy Hưng, Cầu Giấy", dropoff_address="9 Láng Hạ, Đống Đa",
        driver_name="Ngô Đức Thắng", final_fare=141_000,
        requested_at=datetime(2026, 8, 26, 7, 0, tzinfo=UTC))
    out = tokenize_model(detail, vault)
    for name in pii_fields_of(GetRideDetailOutput):
        value = getattr(out, name, None)
        if value:
            assert PLACEHOLDER_RE.fullmatch(value), f"Trường PII {name} chưa được token hoá"


def test_executor_khong_tra_pii_tho_ra_ngoai():
    """Kiểm ở đúng ranh giới mà dữ liệu rời khỏi tầng tool để đi vào prompt."""
    import uuid

    from src.backend.db.connection import get_connection
    from src.backend.db.repository import get_user_by_email
    from src.backend.pii.tokenizer import get_vault
    from src.backend.tools.executor import execute_tool

    customer = get_user_by_email("demo.customer@gsm.vn")["id"]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO conversations (customer_id, thread_id) VALUES (%s,%s) "
                    "RETURNING id", (customer, f"pii-test-{uuid.uuid4().hex[:8]}"))
        conversation_id = str(cur.fetchone()[0])
    try:
        result = execute_tool("get_ride_detail",
                              {"conversation_id": conversation_id,
                               "ride_code": "XSM-LOSTITEM-01"},
                              conversation_id=conversation_id)
        assert result.ok
        assert PLACEHOLDER_RE.fullmatch(result.data.pickup_address)
        assert PLACEHOLDER_RE.fullmatch(result.data.driver_name)

        # Nhưng tool_calls trong DB vẫn phải giữ giá trị THẬT cho CSKH truy vết
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT result->>'driver_name' FROM tool_calls "
                        "WHERE conversation_id = %s", (conversation_id,))
            logged = cur.fetchone()[0]
        assert logged and not PLACEHOLDER_RE.fullmatch(logged), (
            "tool_calls phải lưu giá trị thật — tool trace mất PII thì CSKH không xử lý được ca"
        )
        assert get_vault(conversation_id).detokenize(result.data.driver_name) == logged
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM tool_calls WHERE conversation_id = %s", (conversation_id,))
            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))


# --- Che tren luong stream --------------------------------------------------

def _feed_all(masker, chunks: list[str]) -> str:
    return "".join(masker.feed(c) for c in chunks) + masker.flush()


def test_stream_masker_chiu_duoc_placeholder_bi_cat_doi():
    """Model phát `<ADDR` ở mảnh này và `_48>` ở mảnh sau — ghép nhầm là lộ."""
    from src.backend.pii.tokenizer import StreamMasker

    vault = PiiVault(conversation_id="c1")
    token = vault.placeholder_for("12 Nguyễn Trãi, Thanh Xuân", "ADDR")
    head, tail = token[:4], token[4:]

    out = _feed_all(StreamMasker(vault), ["Điểm đón: ", head, tail, " ạ."])
    assert token not in out, "Placeholder lọt nguyên ra giao diện"
    assert "<ADDR" not in out
    assert "12 ***" in out
    assert out.startswith("Điểm đón: ") and out.endswith(" ạ.")


def test_stream_masker_khong_giu_lai_van_ban_thuong():
    """Dấu '<' bình thường trong câu không được làm nghẽn luồng."""
    from src.backend.pii.tokenizer import StreamMasker

    vault = PiiVault(conversation_id="c1")
    chunks = ["Cước ", "dưới ", "100.000đ ", "thì miễn phí"]
    assert _feed_all(StreamMasker(vault), chunks) == "".join(chunks)


def test_stream_masker_tung_ky_tu_mot():
    """Trường hợp xấu nhất: mỗi mảnh đúng một ký tự."""
    from src.backend.pii.tokenizer import StreamMasker

    vault = PiiVault(conversation_id="c1")
    token = vault.placeholder_for("0912345678", "PHONE")
    text = f"Số {token} nhé"
    out = _feed_all(StreamMasker(vault), list(text))
    assert token not in out and "0912345678" not in out
    assert "0912****78" in out


def test_stream_masker_khong_lam_mat_chu():
    """Ghép lại phải đủ chữ — giữ đuôi mà quên xả là mất chữ cuối câu."""
    from src.backend.pii.tokenizer import StreamMasker

    vault = PiiVault(conversation_id="c1")
    for chunks in (["abc"], ["a", "b", "c"], ["kết thúc bằng dấu <"], ["treo <AD", "DR_"]):
        out = _feed_all(StreamMasker(vault), chunks)
        assert len(out) >= len("".join(chunks)) - 12, f"Mất chữ với {chunks}"
