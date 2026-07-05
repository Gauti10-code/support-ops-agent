import os
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith import traceable

from tools.order_tools import get_order_details, check_refund_eligibility
from tools.refund_tool import issue_refund
from tools.rag_tool import search_policy_docs

load_dotenv()

class AgentState(TypedDict):
  messages: Annotated[list, add_messages]

safe_tools=[get_order_details,check_refund_eligibility,search_policy_docs]
sensitive_tools=[issue_refund]
all_tools=safe_tools+sensitive_tools

llm=ChatOpenAI(model="gpt-4o-mini",temperature=0)
llm_with_tools=llm.bind_tools(all_tools)

SYSTEM_PROMPT = """You are a support operations agent for a company.
You have access to the following tools:
- get_order_details: look up order information by order ID
- check_refund_eligibility: check if an order qualifies for a refund
- issue_refund: actually process and issue a refund (sensitive action)
- search_policy_docs: search company policy and scheme documents

Rules:
- Always use tools to answer — never guess order details or policy rules
- For ANY question about schemes, policies, fund management, investment rules, 
  exit loads, or document content — ALWAYS call search_policy_docs first
- For refund eligibility questions, use check_refund_eligibility
- For actually issuing a refund, use issue_refund
- NEVER say you cannot find information without first calling search_policy_docs
- If a question cannot be answered with your tools, say so clearly
- Be concise and professional"""

def call_llm(state:AgentState):
  messages=[{"role":"system","content":SYSTEM_PROMPT}] + state["messages"]
  response=llm_with_tools.invoke(messages)
  return {"messages":[response]}

safe_tool_node=ToolNode(safe_tools)
sensitive_tool_node=ToolNode(sensitive_tools)

# ---------- Routing ----------

def route_after_llm(state:AgentState):
  last=state["messages"][-1]
  if not hasattr(last,"tool_calls") or not last.tool_calls:
    return END
  tool_name=last.tool_calls[0]["name"]
  if tool_name in [t.name for t in sensitive_tools]:
    return "sensitive_tools"
  return "safe_tools"

# ---------- Build graph ----------
def build_graph(checkpointer):
  builder=StateGraph(AgentState)
  builder.add_node("llm",call_llm)
  builder.add_node("safe_tools",safe_tool_node)
  builder.add_node("sensitive_tools",sensitive_tool_node)
  builder.add_edge(START,"llm")
  builder.add_conditional_edges(
    "llm",
    route_after_llm,
    {"safe_tools":"safe_tools","sensitive_tools":"sensitive_tools",END:END}
  )
  builder.add_edge("safe_tools","llm")
  builder.add_edge("sensitive_tools","llm")

  return builder.compile(checkpointer=checkpointer,interrupt_before=["sensitive_tools"])

@traceable(name="support_ops-agent",tags=["production","support"])
def run_agent(message:str, session_id:str, checkpointer)->dict:
  graph=build_graph(checkpointer)
  config={"configurable":{"thread_id":session_id}}

  graph.invoke(
    {"messages":[{"role":"user","content":message}]},
    config=config
  )
  state=graph.get_state(config)

  if state.next:
        last = state.values["messages"][-1]
        tool_call = last.tool_calls[0]
        return {
            "reply": f"I want to {tool_call['name']} with these details: {tool_call['args']}. Please approve or deny this action.",
            "tools_used": [],
            "pending_approval": True,
            "session_id": session_id
        }

    # Normal response
  messages = state.values["messages"]
  reply = messages[-1].content

  tools_used = []
  for msg in messages:
    if hasattr(msg, "tool_calls") and msg.tool_calls:
      for tc in msg.tool_calls:
        tools_used.append(tc["name"])

  return {
        "reply": reply,
        "tools_used": tools_used,
        "pending_approval": False,
        "session_id": session_id
  }

def resume_agent(approved: bool, session_id: str, checkpointer) -> dict:
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": session_id}}

    if not approved:
        return {
            "reply": "Action cancelled. The refund was not processed.",
            "tools_used": [],
            "pending_approval": False,
            "session_id": session_id
        }

    graph.invoke(None, config=config)
    state = graph.get_state(config)
    reply = state.values["messages"][-1].content

    return {
        "reply": reply,
        "tools_used": ["issue_refund"],
        "pending_approval": False,
        "session_id": session_id
  }