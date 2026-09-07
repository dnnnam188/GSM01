"""FastAPI app cho GSM-01.

Chạy cục bộ:
    .venv/Scripts/python.exe -m uvicorn src.backend.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
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
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from src.backend.agent.graph import ANSWER_SYSTEM, resume_graph
from src.backend.agent.pipeline import run_turn
from src.backend.api.hub import hub
from src.backend.api.limits import SlidingWindowLimiter
from src.backend.api.security import create_access_token, decode_access_token, verify_password
from src.backend.api.ws_auth import WebSocketTicketStore
from src.backend.config.settings import get_settings
from src.backend.db import repository as repo
from src.backend.llm.client import LLMClient, LLMError
from src.backend.pii.detector import mask_text
from src.backend.pii.tokenizer import get_vault

settings = get_settings()
app = FastAPI(title="GSM-01 API", version="0.1.0")
logger = logging.getLogger("gsm01.api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After"],
)
bearer = HTTPBearer(auto_error=False)
_login_limiter = SlidingWindowLimiter(
    settings.login_rate_limit, settings.login_rate_window_seconds)
_chat_limiter = SlidingWindowLimiter(
    settings.chat_rate_limit, settings.chat_rate_window_seconds)
_ws_tickets = WebSocketTicketStore(settings.ws_ticket_ttl_seconds)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Ghi request metadata mà không ghi query string hoặc credential."""
    candidate = request.headers.get("X-Request-ID", "")
    request_id = (
        candidate
        if candidate and len(candidate) <= 80
        and all(char.isalnum() or char in "-_" for char in candidate)
        else str(uuid.uuid4())
    )
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed method=%s path=%s request_id=%s",
            request.method, request.url.path, request_id,
        )
        raise
    duration_ms = round((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method, request.url.path, response.status_code, duration_ms, request_id,
    )
    return response

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
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


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


def require_customer(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    """Điểm hài lòng là tiếng nói của khách. Tài khoản CSKH không được tự chấm hộ."""
    if user["role"] != "customer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ khách hàng mới chấm điểm được")
    return user


class CsatRequest(BaseModel):
    # Chặn ngay ở biên: điểm ngoài 1–5 bị FastAPI trả 422 trước khi chạm tới DB.
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Liveness: process còn chạy, không phụ thuộc database/LLM."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/ready")
async def ready() -> dict[str, Any]:
    """Readiness: chỉ báo xanh khi database có thể nhận query."""
    try:
        await asyncio.to_thread(repo.check_database)
    except Exception as exc:  # noqa: BLE001 - không lộ chi tiết dependency ra ngoài
        logger.warning("readiness_failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Dịch vụ chưa sẵn sàng") from None
    return {"status": "ready", "environment": settings.environment}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    host = request.client.host if request.client else "unknown"
    rate_key = f"{host}:{body.email.lower()}"
    if not _login_limiter.allow(rate_key):
        retry_after = _login_limiter.retry_after(rate_key)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau.",
            headers={"Retry-After": str(retry_after)},
        )
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


@app.post("/api/auth/ws-ticket")
async def create_ws_ticket(
    user: Annotated[dict[str, Any], Depends(require_customer)],
) -> dict[str, Any]:
    """Cấp ticket WebSocket dùng một lần thay cho đưa JWT dài hạn vào URL."""
    ticket, expires_in = _ws_tickets.issue(user)
    return {"ticket": ticket, "expires_in": expires_in}


@app.get("/api/me")
async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    return user


@app.get("/api/dashboard/summary")
async def dashboard(_: Annotated[dict[str, Any], Depends(require_agent)]) -> dict[str, Any]:
    return await asyncio.to_thread(repo.dashboard_summary)


@app.get("/api/dashboard/stats")
async def dashboard_stats(
    _: Annotated[dict[str, Any], Depends(require_agent)],
) -> dict[str, Any]:
    """Thống kê đầy đủ + cảnh báo hạn mức (F13, F14). Chỉ CSKH xem được."""
    return await asyncio.to_thread(repo.dashboard_stats)


@app.post("/api/chat/{thread_id}/csat")
async def submit_csat(
    thread_id: str,
    body: CsatRequest,
    user: Annotated[dict[str, Any], Depends(require_customer)],
) -> dict[str, Any]:
    """Khách chấm điểm phiên vừa rồi (F16).

    Khoá theo `thread_id` vì đó là thứ khung chat cầm trong tay; `conversation_id`
    không bao giờ được gửi ra phía client.
    """
    saved = await asyncio.to_thread(
        repo.save_csat, thread_id, user["id"], body.score, body.comment)
    if saved is None:
        # Không tồn tại và không-phải-của-bạn trả về cùng một câu: nói rõ cái nào
        # là chỉ ra cho người ngoài biết thread_id nào có thật.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy phiên trò chuyện")
    return saved


@app.get("/api/chat/{thread_id}/csat")
async def read_csat(
    thread_id: str,
    user: Annotated[dict[str, Any], Depends(require_customer)],
) -> dict[str, Any]:
    rating = await asyncio.to_thread(repo.get_csat, thread_id, user["id"])
    return {"rating": rating}


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

    amount = f"{decided['amount']:,}".replace(",", ".")
    plain_answer = (
        f"Dạ, yêu cầu hoàn tiền {amount} VNĐ (mã {refund_code}) của anh/chị đã được "
        f"{'phê duyệt' if body.approved else 'xem xét và chưa được duyệt'} ạ."
        + (f" Lý do: {body.reason}" if not body.approved and body.reason else "")
    )

    # Đánh thức graph. Có thể thất bại nếu thread không còn checkpoint — ví dụ ca
    # được tạo ngoài graph, hoặc checkpoint đã bị dọn. Quyết định thì ĐÃ ghi vào
    # DB rồi, nên tuyệt đối không được để lỗi ở bước này nuốt mất nó: vẫn phải
    # báo cho khách, chỉ là bằng câu soạn sẵn thay vì câu do agent viết.
    resumed = False
    answer = plain_answer
    try:
        state = await resume_graph(thread_id, {
            "approved": body.approved,
            "reason": body.reason,
            "agent_email": agent["email"],
        })
        prompt = state.get("answer_prompt")
        if prompt:
            response = get_llm_client().generate(
                prompt, system=ANSWER_SYSTEM, max_tokens=500)
            answer = mask_text(get_vault(thread_id).mask_for_display(response.text))
        resumed = True
    except LLMError as exc:
        resumed = True  # graph đã chạy tiếp, chỉ bước sinh câu chữ là hỏng
        await asyncio.to_thread(
            repo.log_tool_call, thread_id, "generate_answer", {"refund_code": refund_code},
            status="ERROR", error_type="RETRYABLE", error_message=str(exc)[:500])
    except Exception as exc:  # noqa: BLE001 — không được để mất quyết định đã ghi
        await asyncio.to_thread(
            repo.log_tool_call, thread_id, "resume_graph", {"refund_code": refund_code},
            status="ERROR", error_type="FATAL",
            error_message=f"{type(exc).__name__}: {exc}"[:500])

    await asyncio.to_thread(
        repo.insert_message, thread_id, "assistant", answer, intent="refund.request")
    await asyncio.to_thread(repo.set_conversation_status, thread_id, "ACTIVE")

    delivered = await hub.push(thread_id, {
        "type": "hitl_result", "refund_code": refund_code,
        "approved": body.approved, "message": answer,
    })
    return {"refund_code": refund_code, "status": decided["status"], "resumed": resumed,
            "delivered_to_customer": delivered, "message": answer}


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, thread_id: str = "") -> None:
    """Chat streaming.

    Browser gửi one-time ticket trong frame đầu tiên sau khi mở kết nối.
    Access token dài hạn không xuất hiện trong URL WebSocket.
    """
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        await websocket.accept()
        await websocket.send_json({"type": "error", "value": "Origin không được phép"})
        await websocket.close(code=4403)
        return

    await websocket.accept()
    auth_ticket = ""
    try:
        auth_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        if len(auth_raw.encode("utf-8")) <= settings.max_ws_frame_bytes:
            auth_data = json.loads(auth_raw)
            if isinstance(auth_data, dict):
                candidate = auth_data.get("ticket", "")
                auth_ticket = candidate if isinstance(candidate, str) else ""
    except (TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        auth_ticket = ""
    payload = _ws_tickets.consume(auth_ticket)
    if payload is None:
        await websocket.send_json({"type": "error", "value": "Ticket không hợp lệ hoặc đã hết hạn"})
        await websocket.close(code=4401)
        return

    if payload.get("role") != "customer" or not payload.get("id"):
        await websocket.send_json({"type": "error", "value": "Chỉ tài khoản khách hàng dùng được khung chat"})
        await websocket.close(code=4403)
        return

    customer_id = str(payload["id"])
    thread_id = thread_id if len(thread_id) <= 128 else ""
    thread_id = thread_id or f"th-{uuid.uuid4()}"
    # `thread_id` của WebSocket không phải conversation_id; đăng ký vào hub sau
    # lượt đầu tiên, khi đã biết conversation_id thật.
    conversation_id: str | None = None
    await websocket.send_json({"type": "ready", "thread_id": thread_id})

    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=settings.ws_idle_timeout_seconds)
            except TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "value": "Phiên chat đã tạm đóng vì không hoạt động. Anh/chị mở lại giúp em ạ.",
                })
                await websocket.close(code=1000)
                return

            if len(raw.encode("utf-8")) > settings.max_ws_frame_bytes:
                await websocket.send_json({
                    "type": "error",
                    "value": "Tin nhắn quá dài. Anh/chị rút gọn nội dung rồi thử lại giúp em ạ.",
                })
                await websocket.send_json({"type": "done", "intent": None, "degraded": True})
                continue
            try:
                decoded = json.loads(raw)
                message = decoded.get("message", "") if isinstance(decoded, dict) else ""
            except json.JSONDecodeError:
                message = raw
            if not isinstance(message, str):
                message = ""
            message = message.strip()
            if not message:
                continue
            if len(message) > settings.max_message_chars:
                await websocket.send_json({
                    "type": "error",
                    "value": "Tin nhắn quá dài. Anh/chị rút gọn nội dung rồi thử lại giúp em ạ.",
                })
                await websocket.send_json({"type": "done", "intent": None, "degraded": True})
                continue
            if not _chat_limiter.allow(customer_id):
                retry_after = _chat_limiter.retry_after(customer_id)
                await websocket.send_json({
                    "type": "error",
                    "value": "Anh/chị gửi hơi nhanh. Vui lòng thử lại sau ít giây ạ.",
                    "retry_after_seconds": retry_after,
                })
                await websocket.send_json({
                    "type": "done", "intent": None, "degraded": True,
                    "retry_after_seconds": retry_after,
                })
                continue
            if conversation_id is None:
                conversation_id = await asyncio.to_thread(
                    repo.get_or_create_conversation, customer_id, thread_id)
                await hub.register(conversation_id, websocket)
            try:
                async for event in run_turn(customer_id, thread_id, message, get_llm_client()):
                    await websocket.send_json(event)
            except Exception:  # noqa: BLE001 — không được để một lượt lỗi làm sập kết nối
                await websocket.send_json({
                    "type": "error",
                    "value": "Hệ thống gặp sự cố khi xử lý yêu cầu. Anh/chị thử lại giúp em ạ.",
                })
                await websocket.send_json({"type": "done", "intent": None, "degraded": True})
                logger.exception("ws_turn_failed conversation_id=%s", conversation_id)
    except WebSocketDisconnect:
        return
    finally:
        if conversation_id:
            await hub.unregister(conversation_id, websocket)
