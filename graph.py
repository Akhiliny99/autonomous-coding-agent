"""LangGraph orchestration for the coding agent.

Flow:
    planner -> coder -> test --pass--> END
                          `--fail--> diagnoser -> coder (retry, up to max_attempts)
"""
from langgraph.graph import StateGraph, END
from agent.nodes import planner_node, coder_node, diagnoser_node
from agent.sandbox import run_tests_in_sandbox


def test_node(state: dict) -> dict:
    result = run_tests_in_sandbox(state["repo_path"])
    state["tests_passed"] = result["passed"]
    state["last_error"] = None if result["passed"] else result["logs"]
    return state


def route_after_test(state: dict) -> str:
    if state["tests_passed"]:
        return "done"
    if state["attempt"] >= state.get("max_attempts", 3):
        return "give_up"
    return "retry"


def build_graph():
    graph = StateGraph(dict)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("test", test_node)
    graph.add_node("diagnoser", diagnoser_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "test")
    graph.add_conditional_edges("test", route_after_test, {
        "done": END,
        "give_up": END,
        "retry": "diagnoser",
    })
    graph.add_edge("diagnoser", "coder")

    return graph.compile()
