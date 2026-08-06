"""LangGraph agent nodes: planner, coder, diagnoser.

Each node takes the shared state dict, does its job, and returns the
(mutated) state for the next node in the graph.
"""
import json
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"


def call_llm(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def planner_node(state: dict) -> dict:
    prompt = f"""
You are diagnosing a GitHub issue to plan a code fix.

Issue title: {state['issue']['title']}
Issue body: {state['issue']['body']}

Relevant files found:
{chr(10).join(state['relevant_files'])}

Write a short plan (3-5 bullet points) describing what needs to change and in
which file(s).
"""
    state["plan"] = call_llm(prompt)
    return state


def coder_node(state: dict) -> dict:
    file_contents = {}
    for f in state["relevant_files"]:
        try:
            with open(f) as fh:
                file_contents[f] = fh.read()
        except OSError:
            continue

    retry_context = ""
    if state.get("last_error"):
        retry_context = (
            "\nThe previous attempt failed with this test output:\n"
            f"{state['last_error']}\n"
            "Fix the issue causing this failure."
        )

    prompt = f"""
Plan: {state['plan']}

Current file contents:
{json.dumps(file_contents, indent=2)}
{retry_context}

Return ONLY valid JSON mapping file paths to their FULL new content, with no
markdown fences and no extra text:
{{"path/to/file.py": "full new file content"}}
"""
    response = call_llm(prompt)

    # Strip accidental markdown code fences if the model adds them anyway.
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]

    try:
        patches = json.loads(cleaned)
    except json.JSONDecodeError:
        patches = {}

    for path, content in patches.items():
        try:
            with open(path, "w") as fh:
                fh.write(content)
        except OSError:
            continue

    state["attempt"] = state.get("attempt", 0) + 1
    return state


def diagnoser_node(state: dict) -> dict:
    # last_error is already set from the sandbox output (see graph.py's
    # test_node). This node exists as an explicit "diagnose" step in the
    # graph, and is the natural place to add structured traceback parsing
    # later (see README "Possible extensions").
    state["should_retry"] = state["attempt"] < state.get("max_attempts", 3)
    return state
