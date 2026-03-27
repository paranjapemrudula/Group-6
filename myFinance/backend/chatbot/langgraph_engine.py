import os
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

# Define keywords that map user intent to sectors
SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "technology": ["tech", "software", "ai", "cloud", "semiconductor", "chip", "nasdaq"],
    "finance": ["bank", "fintech", "insurance", "asset", "lender", "credit"],
    "healthcare": ["health", "pharma", "biotech", "hospital", "vaccine"],
    "energy": ["oil", "gas", "solar", "wind", "renewable", "power"],
    "consumer": ["retail", "ecommerce", "consumer", "food", "beverage"],
}

DEFAULT_SECTOR = "general"


class ChatState(BaseModel):
    """Graph state holding the rolling conversation and routing metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]
    sector: Optional[str] = None
    # LangGraph may persist the raw LLM metadata here; keep it optional/loosely typed.
    llm_output: Optional[Dict[str, Any]] = None


def _init_messages() -> List[SystemMessage]:
    """Seed the conversation with a finance assistant instruction."""
    return [
        SystemMessage(
            content=(
                "You are MyFinance AI Assistant.\n"
                "Be concise. When a stock/sector is mentioned, tailor the insight to that sector."
            )
        )
    ]


def _classify_sector(question: str) -> str:
    q = question.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword in q for keyword in keywords):
            return sector
    return DEFAULT_SECTOR


def _router(state: ChatState) -> str:
    latest = state["messages"][-1].content if state["messages"] else ""
    sector = _classify_sector(latest)
    state["sector"] = sector
    return sector


def _make_sector_node(sector: str, llm: ChatOpenAI):
    def node(state: ChatState) -> ChatState:
        # Give the model a sector-specific system nudge
        prompt = SystemMessage(
            content=(
                f"Focus your answer on the {sector} sector. "
                "Highlight relevant indicators (growth drivers, risks, recent trends) and give 1-2 tickers if helpful."
            )
        )
        history = state["messages"] + [prompt]
        reply = llm.invoke(history)
        return {**state, "messages": state["messages"] + [reply]}

    return node


def _make_general_node(llm: ChatOpenAI):
    def node(state: ChatState) -> ChatState:
        reply = llm.invoke(state["messages"])
        return {**state, "messages": state["messages"] + [reply]}

    return node


def build_sector_graph() -> StateGraph:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        temperature=float(os.getenv("CHATBOT_TEMPERATURE", "0.4")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    builder = StateGraph(ChatState)

    builder.add_node("router", _router)
    builder.add_node(DEFAULT_SECTOR, _make_general_node(llm))

    for sector in SECTOR_KEYWORDS:
        builder.add_node(sector, _make_sector_node(sector, llm))

    builder.add_conditional_edges(
        "router",
        lambda state: state.get("sector", DEFAULT_SECTOR),
        list(SECTOR_KEYWORDS.keys()) + [DEFAULT_SECTOR],
    )

    for sector in SECTOR_KEYWORDS:
        builder.add_edge(sector, END)
    builder.add_edge(DEFAULT_SECTOR, END)

    builder.set_entry_point("router")

    return builder.compile()


def new_session_state() -> ChatState:
    return {"messages": _init_messages(), "sector": None}
