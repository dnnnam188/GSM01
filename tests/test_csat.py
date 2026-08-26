"""Thu thập điểm hài lòng cuối phiên (T-015 · F16).

    .venv/Scripts/python.exe -m pytest tests/test_csat.py -q

Gọi thẳng vào ứng dụng ASGI nên không cần dựng server. Trọng tâm không phải
"ghi được điểm hay không" — mà là **ai được ghi lên phiên của ai**: chấm điểm là
ghi dữ liệu, và ghi dữ liệu lên hội thoại của người khác là một lỗ hổng thật.
"""
from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest

from src.backend.db.connection import get_connection
from src.backend.db.repository import dashboard_stats, get_csat, save_csat
from src.backend.main import app


def _login(email: str) -> str:
    from src.backend.api.security import create_access_token
    from src.backend.db.repository import get_user_by_email
    u = get_user_by_email(email)
    return create_access_token(u["id"], u["email"], u["role"])


@pytest.fixture(scope="module")
def customer() -> dict:
    from src.backend.db.repository import get_user_by_email
    return get_user_by_email("demo.customer@gsm.vn")


@pytest.fixture
def phien(customer):
    """Một hội thoại dùng riêng cho bài kiểm, xoá sạch sau khi xong."""
    thread = f"csat-{uuid.uuid4().hex[:10]}"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO conversations (customer_id, thread_id) VALUES (%s,%s) "
                    "RETURNING id", (customer["id"], thread))
        conv = str(cur.fetchone()[0])
    yield {"thread_id": thread, "conversation_id": conv}
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM csat_ratings WHERE conversation_id = %s", (conv,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (conv,))


def _auth(email: str) -> dict:
    return {"Authorization": f"Bearer {_login(email)}"}


def call(method: str, url: str, **kwargs) -> httpx.Response:
    """Gọi thẳng vào ứng dụng ASGI, không qua mạng và không cần dựng server.

    Bọc trong `asyncio.run` để test vẫn là hàm đồng bộ — dự án chưa có
    `pytest-asyncio`, và thêm một phụ thuộc chỉ để viết `async def test_` là cái
    giá không đáng.
    """
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.request(method, url, **kwargs)
    return asyncio.run(go())


# --- Đường chính -----------------------------------------------------------
def test_ghi_duoc_diem(phien, customer):
    saved = save_csat(phien["thread_id"], customer["id"], 5, "Nhanh và đúng ý")
    assert saved["score"] == 5
    assert get_csat(phien["thread_id"], customer["id"])["score"] == 5


def test_cham_lai_thi_cap_nhat_chu_khong_no(phien, customer):
    """Bảng có UNIQUE trên conversation_id — không có ON CONFLICT là lần hai lỗi 500."""
    save_csat(phien["thread_id"], customer["id"], 2, None)
    save_csat(phien["thread_id"], customer["id"], 4, "Nghĩ lại thấy ổn")
    assert get_csat(phien["thread_id"], customer["id"]) == {
        "score": 4, "comment": "Nghĩ lại thấy ổn"}
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM csat_ratings WHERE conversation_id = %s",
                    (phien["conversation_id"],))
        assert cur.fetchone()[0] == 1, "phải cập nhật một dòng, không đẻ thêm dòng mới"


# --- Quyền: phần đáng lo nhất ---------------------------------------------
def test_khong_cham_duoc_len_phien_cua_nguoi_khac(phien):
    """Đây là lý do bài kiểm này tồn tại."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE role = 'customer' AND email <> %s LIMIT 1",
                    ("demo.customer@gsm.vn",))
        row = cur.fetchone()
    if not row:
        pytest.skip("chỉ có một tài khoản khách trong dữ liệu mẫu")
    assert save_csat(phien["thread_id"], str(row[0]), 1, "phá hoại") is None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM csat_ratings WHERE conversation_id = %s",
                    (phien["conversation_id"],))
        assert cur.fetchone()[0] == 0, "đã ghi được lên hội thoại của người khác"


def test_thread_khong_ton_tai_tra_none(customer):
    assert save_csat("khong-he-co-thread-nay", customer["id"], 5, None) is None


# --- Qua HTTP --------------------------------------------------------------
def test_http_khach_cham_duoc(phien):
    r = call("POST", f"/api/chat/{phien['thread_id']}/csat",
                          json={"score": 4}, headers=_auth("demo.customer@gsm.vn"))
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 4
    r = call("GET", f"/api/chat/{phien['thread_id']}/csat",
             headers=_auth("demo.customer@gsm.vn"))
    assert r.json()["rating"]["score"] == 4


def test_http_cskh_khong_cham_ho_duoc(phien):
    """Điểm hài lòng là tiếng nói của khách. CSKH tự chấm hộ thì con số vô nghĩa."""
    r = call("POST", f"/api/chat/{phien['thread_id']}/csat",
                          json={"score": 5}, headers=_auth("agent01@gsm.vn"))
    assert r.status_code == 403


def test_http_khong_token_thi_chan(phien):
    r = call("POST", f"/api/chat/{phien['thread_id']}/csat", json={"score": 5})
    assert r.status_code == 401


@pytest.mark.parametrize("score", [0, 6, -1, 100])
def test_http_diem_ngoai_khoang_bi_chan_o_bien(phien, score):
    """Chặn ở biên bằng Pydantic, không để chạm tới DB rồi mới nhờ CHECK constraint."""
    r = call("POST", f"/api/chat/{phien['thread_id']}/csat",
                          json={"score": score}, headers=_auth("demo.customer@gsm.vn"))
    assert r.status_code == 422


def test_http_phien_la_tra_404_khong_lo_thong_tin():
    r = call("POST", "/api/chat/th-khong-co-that/csat",
                          json={"score": 5}, headers=_auth("demo.customer@gsm.vn"))
    assert r.status_code == 404


# --- Nối vào dashboard -----------------------------------------------------
def test_diem_chay_vao_dashboard(phien, customer):
    truoc = dashboard_stats()["csat"]
    save_csat(phien["thread_id"], customer["id"], 5, None)
    sau = dashboard_stats()["csat"]
    assert sau["count"] == truoc["count"] + 1
    assert sau["average"] is not None, "có điểm rồi mà dashboard vẫn trả None"
