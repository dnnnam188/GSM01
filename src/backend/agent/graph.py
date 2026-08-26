"""LangGraph điều phối agent (T-004).

Vì sao điều phối tool bằng **luật tường minh** chứ không để LLM tự chọn tool:

1. Router đã trả về `intent` + `slots` trong một lần gọi. Để LLM chọn tool nữa là
   thêm một lượt gọi model trên đường tới token đầu tiên — phá ngân sách 3 giây.
2. Ánh xạ intent → tool đã được chốt trong `docs/intent-taxonomy.md` và
   `TOOL_REGISTRY.intents`. Cho LLM chọn lại mỗi lượt là mở đường cho nó chọn sai
   một cách không tái lập được, trong khi bảng ánh xạ thì kiểm thử được.
3. Tool ghi dữ liệu (đặt xe, huỷ, hoàn tiền) là thao tác mất tiền thật. Quyền quyết
   định gọi hay không nên nằm ở nơi đọc được, không nằm trong trọng số của model.

LLM vẫn giữ phần nó làm tốt: hiểu ý định, trích thông tin, và diễn đạt câu trả lời.

Câu trả lời cuối **không** sinh trong graph mà do `pipeline.py` stream ra, vì
WebSocket cần từng token một để đạt ngưỡng TTFT. Graph dừng ở bước dựng xong
`answer_prompt`. Điểm dừng HITL của T-011 nằm ở `tool_node`, tức là **trước**
bước đó, nên tách như vậy không cản trở gì.
"""
from __future__ import annotations

import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.backend.agent.router import route
from src.backend.db import repository as repo
from src.backend.llm.client import LLMClient
from src.backend.rag.retriever import retrieve
from src.backend.tools.executor import derive_refund_evidence, execute_tool


def _merge_list(left: list, right: list) -> list:
    return (left or []) + (right or [])


class AgentState(TypedDict, total=False):
    # Đầu vào
    customer_id: str
    conversation_id: str
    message: str
    history: list[dict[str, Any]]
    # Router
    intent: str
    confidence: float
    slots: dict[str, Any]
    missing_slots: list[str]
    standalone_query: str
    # Kết quả các bước
    chunks: list[Any]
    tool_results: Annotated[list[dict[str, Any]], _merge_list]
    clarify_question: str
    answer_prompt: str
    degraded: bool
    pending_hitl: dict[str, Any] | None


# Intent nào cần mã chuyến mới làm được việc
NEEDS_RIDE_CODE = {"booking.cancel", "booking.modify", "refund.request",
                   "complaint.driver", "complaint.lost_item"}
NEEDS_RAG = {"policy.faq", "fare.inquiry", "booking.cancel", "refund.request",
             "complaint.driver", "complaint.lost_item"}

ANSWER_SYSTEM = """Bạn là trợ lý CSKH của hãng gọi xe điện Xanh SM. Trả lời bằng tiếng Việt,
ngắn gọn, lịch sự, xưng "em" và gọi khách là "anh/chị".

QUY TẮC BẮT BUỘC:
- Chỉ dùng thông tin trong phần TRI THỨC CHÍNH SÁCH và KẾT QUẢ THAO TÁC bên dưới.
  Không có thì nói thẳng là chưa có thông tin.
- Không bịa số tiền, không bịa mã chuyến, không bịa chính sách.
- Không đọc số điện thoại, địa chỉ đầy đủ hay tên tài xế cho khách.
- KẾT QUẢ THAO TÁC là việc hệ thống ĐÃ THỰC HIỆN XONG. Hãy thuật lại đúng như vậy,
  kèm mã chuyến / mã phiếu / số tiền có trong đó.
- Nếu KẾT QUẢ THAO TÁC báo lỗi, xin lỗi và nói lại đúng nội dung lỗi bằng lời dễ hiểu.
  Tuyệt đối không nói thao tác đã thành công.
- Nếu yêu cầu hoàn tiền đang chờ nhân viên duyệt, nói rõ là đã chuyển bộ phận phụ trách
  và nêu thời gian phản hồi dự kiến. Không hứa chắc là sẽ được duyệt.
- Nếu `refund_eligibility` báo không đủ điều kiện, hãy giải thích NHẸ NHÀNG và NÊU RÕ CĂN CỨ
  đối soát, rồi mời khách cung cấp thêm bằng chứng nếu vẫn thấy chưa thoả đáng.
  Không tạo cảm giác đổ lỗi cho khách."""


# ===========================================================================
# Các node
# ===========================================================================
def route_node(state: AgentState) -> dict[str, Any]:
    started = time.perf_counter()
    result = route(state["message"], state.get("history"), LLMClient())
    # Ghi vào tool_calls: phân loại ý định cũng là một lời gọi model, và F10 yêu
    # cầu log ĐẦY ĐỦ. Bỏ dòng này là tool trace của CSKH mất mất bước đầu tiên.
    repo.log_tool_call(
        state["conversation_id"], "route_intent", {"message": state["message"]},
        result={"intent": result.intent, "confidence": result.confidence,
                "slots": result.slots, "missing_slots": result.missing_slots,
                "standalone_query": result.standalone_query},
        latency_ms=int((time.perf_counter() - started) * 1000))
    return {
        "intent": result.intent,
        "confidence": result.confidence,
        "slots": result.slots,
        "missing_slots": result.missing_slots,
        "standalone_query": result.standalone_query,
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    try:
        chunks = retrieve(state.get("standalone_query") or state["message"], top_k=3)
        repo.log_tool_call(
            state["conversation_id"], "retrieve_policy",
            {"query": state.get("standalone_query"), "original_message": state["message"]},
            result={"sources": [c.source_file for c in chunks],
                    "top_similarity": round(chunks[0].similarity, 3) if chunks else None})
        return {"chunks": chunks}
    except Exception as exc:  # noqa: BLE001 — truy hồi hỏng không được làm đổ cả lượt
        repo.log_tool_call(
            state["conversation_id"], "retrieve_policy", {"query": state.get("standalone_query")},
            status="ERROR", error_type="RETRYABLE", error_message=str(exc)[:500])
        return {"chunks": [], "degraded": True}


def _resolve_ride_code(state: AgentState) -> str | None:
    """Khách thường không nhớ mã chuyến. Suy ra từ chuyến đang hoạt động hoặc gần nhất."""
    code = state.get("slots", {}).get("ride_code")
    if code:
        return code
    intent = state["intent"]
    wanted = (["ASSIGNED", "IN_PROGRESS"] if intent in ("booking.cancel", "booking.modify")
              else ["COMPLETED"])
    result = execute_tool("get_ride_history", {
        "conversation_id": state["conversation_id"], "customer_id": state["customer_id"],
        "limit": 3, "since_days": 30, "status_filter": wanted,
    }, conversation_id=state["conversation_id"])
    if result.ok and len(result.data.rides) == 1:
        return result.data.rides[0].ride_code
    return None


def tool_node(state: AgentState) -> dict[str, Any]:
    """Gọi tool theo luật ánh xạ intent → tool."""
    intent = state["intent"]
    conv = state["conversation_id"]
    slots = state.get("slots", {})
    calls: list[dict[str, Any]] = []

    def run(name: str, payload: dict[str, Any]) -> None:
        result = execute_tool(name, {"conversation_id": conv, **payload}, conversation_id=conv)
        calls.append({
            "tool": name,
            "ok": result.ok,
            "replayed": result.replayed,
            "data": result.data.model_dump(mode="json") if result.ok and result.data else None,
            "error": result.error.model_dump(mode="json") if result.error else None,
        })

    ride_code = _resolve_ride_code(state) if intent in NEEDS_RIDE_CODE else None

    if intent == "trip.lookup":
        if slots.get("ride_code"):
            run("get_ride_detail", {"ride_code": slots["ride_code"]})
        else:
            run("get_ride_history", {"customer_id": state["customer_id"], "limit": 5,
                                     "since_days": 90})

    elif intent == "fare.inquiry" and slots.get("pickup") and slots.get("dropoff"):
        run("estimate_fare", {
            "pickup_address": slots["pickup"], "dropoff_address": slots["dropoff"],
            "service_type": slots.get("service_type", "GREENCAR"),
        })

    elif intent == "booking.create":
        run("book_ride", {
            "customer_id": state["customer_id"], "pickup_address": slots.get("pickup", ""),
            "dropoff_address": slots.get("dropoff", ""),
            "service_type": slots.get("service_type", "GREENCAR"),
        })

    elif intent == "booking.cancel" and ride_code:
        run("cancel_ride", {"ride_code": ride_code, "reason": state["message"][:300]})

    elif intent == "booking.modify" and ride_code:
        run("modify_ride", {"ride_code": ride_code,
                            "new_dropoff_address": slots.get("dropoff"),
                            "add_stop_address": slots.get("stop")})

    elif intent == "refund.request" and ride_code:
        # Xem chi tiết chuyến TRƯỚC, để câu trả lời nêu được bằng chứng
        run("get_ride_detail", {"ride_code": ride_code})
        # Số tiền hoàn do HỆ THỐNG suy ra từ dữ liệu, không lấy theo lời khai của
        # khách: khách thường không biết mình được hoàn bao nhiêu, và để khách tự
        # khai số tiền là mở đường cho gian lận.
        evidence = derive_refund_evidence(ride_code)
        if evidence:
            run("request_refund", {
                "customer_id": state["customer_id"], "ride_code": ride_code,
                "amount": evidence["amount"], "reason_code": evidence["reason_code"],
                "reason_detail": f"{evidence['evidence']} | Khách trình bày: "
                                 f"{state['message'][:500]}",
            })
            calls.append({"tool": "refund_eligibility", "ok": True, "replayed": False,
                          "data": evidence, "error": None})
        else:
            # Không đủ điều kiện cũng là một kết quả — agent phải từ chối đúng,
            # chứ không chỉ biết đồng ý đúng.
            calls.append({
                "tool": "refund_eligibility", "ok": True, "replayed": False,
                "data": {"eligible": False,
                         "explanation": "Đối soát dữ liệu chuyến không thấy dấu hiệu thu sai: "
                                        "không có giao dịch trùng, phí huỷ thu đúng quy định, "
                                        "quãng đường và cước phí khớp với lộ trình đã báo."},
                "error": None})

    elif intent in ("complaint.driver", "complaint.lost_item") and ride_code:
        category = "LOST_ITEM" if intent == "complaint.lost_item" else "DRIVER_CONDUCT"
        run("create_ticket", {
            "customer_id": state["customer_id"], "ride_code": ride_code,
            "category": category, "description": state["message"][:2000],
            "severity": "HIGH" if intent == "complaint.lost_item" else "NORMAL",
        })

    # Yêu cầu hoàn tiền vượt ngưỡng — T-011 sẽ biến chỗ này thành interrupt() thật
    pending = next(
        (c for c in calls
         if c["tool"] == "request_refund" and c["ok"]
         and c["data"] and c["data"].get("status") == "PENDING_HITL"),
        None)
    return {"tool_results": calls, "pending_hitl": pending["data"] if pending else None}


def clarify_node(state: AgentState) -> dict[str, Any]:
    """Thiếu thông tin thì hỏi lại, tuyệt đối không đoán bừa rồi gọi tool ghi dữ liệu."""
    missing = state.get("missing_slots") or []
    intent = state["intent"]
    if intent in NEEDS_RIDE_CODE and not state.get("slots", {}).get("ride_code"):
        result = execute_tool("get_ride_history", {
            "conversation_id": state["conversation_id"], "customer_id": state["customer_id"],
            "limit": 5, "since_days": 90,
        }, conversation_id=state["conversation_id"])
        if result.ok and result.data.rides:
            listing = "\n".join(
                f"- {r.ride_code} · {r.service_type} · {r.requested_at:%d/%m %H:%M}"
                f"{f' · {r.final_fare:,} VNĐ'.replace(',', '.') if r.final_fare else ''}"
                for r in result.data.rides)
            return {"clarify_question":
                    f"Để xử lý giúp anh/chị, em cần biết là chuyến nào ạ. "
                    f"Đây là các chuyến gần đây của anh/chị:\n{listing}"}
    labels = {"pickup": "điểm đón", "dropoff": "điểm đến", "amount": "số tiền",
              "service_type": "loại xe", "ride_code": "mã chuyến",
              "item_description": "món đồ bị bỏ quên"}
    needed = ", ".join(labels.get(m, m) for m in missing) or "thêm một chút thông tin"
    return {"clarify_question": f"Anh/chị cho em xin {needed} để em xử lý giúp ạ."}


def answer_node(state: AgentState) -> dict[str, Any]:
    """Dựng prompt cho câu trả lời cuối. Việc stream do pipeline làm."""
    parts: list[str] = []
    history = state.get("history") or []
    if history:
        lines = [f"{'Khách' if m['role'] == 'user' else 'Trợ lý'}: {m['content'][:400]}"
                 for m in history[-6:]]
        parts.append("LỊCH SỬ HỘI THOẠI:\n" + "\n".join(lines))

    chunks = state.get("chunks") or []
    if chunks:
        parts.append("TRI THỨC CHÍNH SÁCH:\n" + "\n\n---\n\n".join(
            f"(Nguồn: {c.source_file})\n{c.content}" for c in chunks))

    results = state.get("tool_results") or []
    if results:
        lines = []
        for call in results:
            if call["ok"]:
                note = " (đã thực hiện trước đó, không làm lại)" if call["replayed"] else ""
                lines.append(f"- {call['tool']}{note}: {call['data']}")
            else:
                lines.append(f"- {call['tool']} THẤT BẠI: {call['error']['message_for_user']}")
        parts.append("KẾT QUẢ THAO TÁC (hệ thống đã thực hiện):\n" + "\n".join(lines))

    parts.append(f"Ý ĐỊNH ĐÃ PHÂN LOẠI: {state.get('intent')}")
    parts.append(f"TIN NHẮN CỦA KHÁCH:\n{state['message']}")
    return {"answer_prompt": "\n\n".join(parts)}


# ===========================================================================
# Rẽ nhánh
# ===========================================================================
def after_route(state: AgentState) -> str:
    intent = state["intent"]
    slots = state.get("slots", {})

    if intent == "booking.create" and not (slots.get("pickup") and slots.get("dropoff")):
        return "clarify"
    if intent in NEEDS_RIDE_CODE and not slots.get("ride_code"):
        # Suy ra được đúng một chuyến thì đi tiếp, nhiều/không có thì hỏi lại
        return "tools" if _resolve_ride_code(state) else "clarify"
    if intent in NEEDS_RAG:
        return "retrieve"
    if intent == "other":
        return "answer"
    return "tools"


def after_retrieve(state: AgentState) -> str:
    return "tools" if state["intent"] != "policy.faq" else "answer"


def build_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("route", route_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("tools", tool_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", after_route,
                                {"retrieve": "retrieve", "tools": "tools",
                                 "clarify": "clarify", "answer": "answer"})
    graph.add_conditional_edges("retrieve", after_retrieve,
                                {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "answer")
    graph.add_edge("clarify", END)
    graph.add_edge("answer", END)
    return graph.compile()


_COMPILED: Any = None


def get_graph() -> Any:
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_graph()
    return _COMPILED


async def run_graph(customer_id: str, conversation_id: str, message: str,
                    history: list[dict[str, Any]]) -> AgentState:
    """Chạy graph tới khi dựng xong prompt trả lời (hoặc câu hỏi làm rõ)."""
    state: AgentState = {
        "customer_id": customer_id, "conversation_id": conversation_id,
        "message": message, "history": history, "tool_results": [],
    }
    return await get_graph().ainvoke(state)
