"""Đọc biến môi trường phải chịu được rác dán nhầm.

Bản deploy trên Render đã chết ngay lúc khởi động vì `JWT_EXPIRE_MINUTES` mang giá
trị `720` kèm một dấu backtick ở cuối — dấu vết của việc sao chép từ văn bản có
định dạng mã. Thông báo lỗi khi đó không hề nói biến nào sai.
"""
from __future__ import annotations

import pytest

from src.backend.config.env import env_int, env_list, env_str


@pytest.mark.parametrize("raw", ["720`", "`720`", " 720 ", '"720"', "'720'", "\t720\n"])
def test_so_nguyen_dinh_rac_van_doc_duoc(monkeypatch, raw):
    monkeypatch.setenv("X_INT", raw)
    assert env_int("X_INT", 1) == 720


@pytest.mark.parametrize("raw", ["`gemini-3.5-flash-lite`", " gemini-3.5-flash-lite ",
                                 '"gemini-3.5-flash-lite"'])
def test_chuoi_dinh_rac_van_doc_duoc(monkeypatch, raw):
    monkeypatch.setenv("X_STR", raw)
    assert env_str("X_STR") == "gemini-3.5-flash-lite"


def test_thieu_bien_thi_dung_mac_dinh(monkeypatch):
    monkeypatch.delenv("X_MISSING", raising=False)
    assert env_int("X_MISSING", 42) == 42
    assert env_str("X_MISSING", "mac-dinh") == "mac-dinh"


def test_bien_rong_coi_nhu_khong_dat(monkeypatch):
    """Render hay để lại biến rỗng khi người dùng xoá giá trị mà quên xoá dòng."""
    monkeypatch.setenv("X_EMPTY", "   ")
    assert env_int("X_EMPTY", 7) == 7
    assert env_str("X_EMPTY", "mac-dinh") == "mac-dinh"


def test_gia_tri_sai_that_thi_bao_loi_neu_dich_danh_bien(monkeypatch):
    monkeypatch.setenv("GEMINI_RPM", "muoi lam")
    with pytest.raises(RuntimeError) as exc:
        env_int("GEMINI_RPM", 15)
    message = str(exc.value)
    assert "GEMINI_RPM" in message, "Phải nêu tên biến, nếu không người deploy phải đọc traceback"
    assert "muoi lam" in message, "Phải nêu giá trị đang sai"


def test_danh_sach_cach_nhau_bang_dau_phay(monkeypatch):
    monkeypatch.setenv("X_LIST", "`https://a.vercel.app` , https://b.vercel.app ,,")
    assert env_list("X_LIST") == ["https://a.vercel.app", "https://b.vercel.app"]


def test_moi_bien_so_cua_du_an_deu_di_qua_env_int():
    """Chặn hồi quy: thêm biến số mới mà quên dùng env_int là lặp lại đúng sự cố cũ."""
    import pathlib
    import re

    for path in ("src/backend/config/settings.py", "src/backend/llm/client.py"):
        source = pathlib.Path(path).read_text(encoding="utf-8")
        assert not re.search(r"int\(os\.getenv", source), (
            f"{path} còn dùng int(os.getenv(...)) — phải dùng env_int() để chịu được rác dán nhầm."
        )
