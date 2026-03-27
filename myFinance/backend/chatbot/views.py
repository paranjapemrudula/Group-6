from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain_core.messages import HumanMessage
from .langgraph_engine import build_sector_graph, new_session_state
import json

# Store chatbot per session (simple approach)
chatbot_sessions = {}


def _get_session(session_id: str):
    if session_id not in chatbot_sessions:
        chatbot_sessions[session_id] = {
            "graph": build_sector_graph(),
            "state": new_session_state(),
        }
    return chatbot_sessions[session_id]


@csrf_exempt
def finance_chat(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default")

        session = _get_session(session_id)
        state = session["state"]

        # push new human message into the conversation state
        state["messages"].append(HumanMessage(content=user_message))

        result = session["graph"].invoke(state)
        session["state"] = result
        reply = result["messages"][-1].content if result.get("messages") else ""

        return JsonResponse({
            "status": "success",
            "reply": reply,
            "session_id": session_id,
            "sector": result.get("sector"),
        })

    return JsonResponse({"error": "Only POST allowed"}, status=405)
