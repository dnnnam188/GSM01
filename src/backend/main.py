"""FastAPI app cho GSM-01.

Chạy cục bộ:
    .venv/Scripts/python.exe -m uvicorn src.backend.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid

# PHẢI đặt trước khi uvicorn tạo event loop. Trên Windows, vòng lặp mặc định là
# ProactorEventLoop, mà `psycopg` bản async KHÔNG chạy được trên đó — checkpointer
# Postgres của LangGraph sẽ hỏng mọi kết nối với thông báo
# "Psycopg cannot use the 'ProactorEventLoop' to run in async mode".
# Trên Linux (môi trường Render) vòng lặp mặc định vốn đã là Selector nên đoạn này
# không có tác dụng gì — nó chỉ để máy phát triển Windows chạy được như production.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from src.backend.agent.graph import ANSWER_SYSTEM, resume_graph
from src.backend.agent.pipeline import run_turn
from src.backend.api.hub import hub
from src.backend.api.security import create_access_token, decode_access_token, verify_password
from src.backend.config.settings import get_settings
from src.backend.db import repository as repo
from src.backend.llm.client import LLMClient, LLMError
from src.backend.pii.detector import mask_text
from src.backend.pii.tokenizer import get_vault

settings = get_settings()
app = FastAPI(title="GSM-01 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bearer = HTTPBearer(auto_error=False)

# Một client dùng chung cho cả tiến trình: nó giữ connection pool của httpx,
# tạo mới mỗi request sẽ đội thêm hàng trăm ms bắt tay TLS vào ngân sách 3 giây.
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# ---------------------------------------------------------------------------
# Mô hình dữ liệu
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class HitlDecision(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=1000)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    full_name: str


# ---------------------------------------------------------------------------
# Xác thực
# ---------------------------------------------------------------------------
def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thiếu token")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token đã hết hạn") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ") from exc
    return {"id": payload["sub"], "email": payload["email"], "role": payload["role"]}


def require_agent(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    """Chặn khách hàng chạm vào dữ liệu vận hành. Kiểm ở server, không ở giao diện."""
    if user["role"] != "agent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ nhân viên CSKH mới được truy cập")
    return user


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "environment": settings.environment}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    user = await asyncio.to_thread(repo.get_user_by_email, body.email)
    # Cùng một thông báo cho cả hai trường hợp, để không lộ email nào có tồn tại
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")
    if not user["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khoá")
    return LoginResponse(
        access_token=create_access_token(user["id"], user["email"], user["role"]),
        user_id=user["id"], email=user["email"], role=user["role"], full_name=user["full_name"],
    )


@app.get("/api/me")
async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    return user


@app.get("/api/dashboard/summary")
async def dashboard(_: Annotated[dict[str, Any], Depends(require_agent)]) -> dict[str, Any]:
    return await asyncio.to_thread(repo.dashboard_summary)


@app.get("/api/conversations/{conversation_id}/transcript")
async def transcript(
    conversation_id: str,
    _: Annotated[dict[str, Any], Depends(require_agent)],
) -> dict[str, Any]:
    return await asyncio.to_thread(repo.conversation_transcript, conversation_id)


@app.get("/api/hitl/queue")
async def hitl_queue(_: Annotated[dict[str, Any], Depends(require_agent)]) -> dict[str, Any]:
    items = await asyncio.to_thread(repo.hitl_queue)
    return {"pending": items, "count": len(items)}


@app.post("/api/hitl/{refund_code}/decide")
async def hitl_decide(
    refund_code: str,
    body: HitlDecision,
    agent: Annotated[dict[str, Any], Depends(require_agent)],
) -> dict[str, Any]:
    """CSKH duyệt hoặc từ chối, rồi ĐÁNH THỨC graph đang treo (ADR-003).

    Thứ tự có chủ ý: ghi quyết định xuống DB **trước**, đánh thức graph **sau**.
    Nếu đảo lại mà bước ghi hỏng, khách đã nhận thông báo được duyệt trong khi hệ
    thống không có bản ghi nào — sai lệch đó không sửa được.
    """
    if not body.approved and not (body.reason or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Từ chối hoàn tiền bắt buộc phải nêu lý do")

    decided = await asyncio.to_thread(
        repo.decide_refund, refund_code, approved=body.approved,
        agent_id=agent["id"], reason=body.reason)
    if decided is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Yêu cầu này không còn ở trạng thái chờ duyệt "
                            "(có thể đã được người khác xử lý)")

    thread_id = decided["resume_thread_id"] or decided["conversation_id"]
    if not thread_id:
        return {"refund_code": refund_code, "status": decided["status"],
                "resumed": False, "delivered_to_customer": 0,
                "note": "Không có phiên hội thoại để đánh thức"}

    state = await resume_graph(thread_id, {
        "approved": body.approved,
        "reason": body.reason,
        "agent_email": agent["email"],
    })

    # Graph chạy tiếp tới answer_node và dựng xong prompt. Sinh câu trả lời rồi
    # đẩy về đúng phiên của khách.
    answer = ""
    try:
        response = get_llm_client().generate(
            state.get("answer_prompt", ""), system=ANSWER_SYSTEM, max_tokens=500)
        answer = mask_text(get_vault(thread_id).mask_for_display(response.text))
    except LLMError:
        amount = f"{decided['amount']:,}".replace(",", ".")
        answer = (
            f"Dạ, yêu cầu hoàn tiền {amount} VNĐ (mã {refund_code}) của anh/chị đã được "
            f"{'phê duyệt' if body.approved else 'xem xét và chưa được duyệt'} ạ."
        )

    await asyncio.to_thread(
        repo.insert_message, thread_id, "assistant", answer, intent="refund.request")
    await asyncio.to_thread(repo.set_conversation_status, thread_id, "ACTIVE")

    delivered = await hub.push(thread_id, {
        "type": "hitl_result", "refund_code": refund_code,
        "approved": body.approved, "message": answer,
    })
    return {"refund_code": refund_code, "status": decided["status"], "resumed": True,
            "delivered_to_customer": delivered, "message": answer}


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = "", thread_id: str = "") -> None:
    """Chat streaming.

    Token đi qua query string chứ không qua header: WebSocket API của trình duyệt
    không cho đặt header tuỳ ý. Đây là hạn chế của nền tảng, không phải lựa chọn.
    """
    await websocket.accept()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        await websocket.send_json({"type": "error", "value": "Token không hợp lệ hoặc đã hết hạn"})
        await websocket.close(code=4401)
        return

    if payload["role"] != "customer":
        await websocket.send_json({"type": "error", "value": "Chỉ tài khoản khách hàng dùng được khung chat"})
        await websocket.close(code=4403)
        return

    customer_id = payload["sub"]
    thread_id = thread_id or f"th-{uuid.uuid4()}"
    # `thread_id` của WebSocket không phải conversation_id; đăng ký vào hub sau
    # lượt đầu tiên, khi đã biết conversation_id thật.
    conversation_id: str | None = None
    await websocket.send_json({"type": "ready", "thread_id": thread_id})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw).get("message", "").strip()
            except json.JSONDecodeError:
                message = raw.strip()
            if not message:
                continue
            if conversation_id is None:
                conversation_id = await asyncio.to_thread(
                    repo.get_or_create_conversation, customer_id, thread_id)
                await hub.register(conversation_id, websocket)
            try:
                async for event in run_turn(customer_id, thread_id, message, get_llm_client()):
                    await websocket.send_json(event)
            except Exception as exc:  # noqa: BLE001 — không được để một lượt lỗi làm sập kết nối
                await websocket.send_json({
                    "type": "error",
                    "value": "Hệ thống gặp sự cố khi xử lý yêu cầu. Anh/chị thử lại giúp em ạ.",
                })
                await websocket.send_json({"type": "done", "intent": None, "degraded": True})
                print(f"[ws_chat] lỗi khi xử lý lượt: {type(exc).__name__}: {exc}")
    except WebSocketDisconnect:
        return
    finally:
        if conversation_id:
            await hub.unregister(conversation_id, websocket)
