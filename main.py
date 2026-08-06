"""Entry point: fetches a GitHub issue, indexes the repo, runs the agent
graph (plan -> code -> test -> retry-if-needed), and opens a PR on success.

Setup:
    1. docker build -t coding-agent-sandbox:latest -f docker/Dockerfile.sandbox .
    2. pip install -r requirements.txt --break-system-packages
    3. export GROQ_API_KEY=...   export GITHUB_TOKEN=...
    4. Edit REPO_FULL_NAME / ISSUE_NUMBER below to point at your own test repo.
    5. python main.py
"""
import os
from agent.github_tools import fetch_issue, clone_repo, create_branch_and_commit, open_pr
from agent.repo_context import index_repo, get_relevant_files
from agent.graph import build_graph

# --- Configure your target here ---
REPO_FULL_NAME = "Akhiliny99/agent-test-repo"
ISSUE_NUMBER = 1
LOCAL_PATH = "./workdir/target-repo"
MAX_ATTEMPTS = 3
# -----------------------------------


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Set the GITHUB_TOKEN environment variable first.")
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("Set the GROQ_API_KEY environment variable first.")

    print(f"Fetching issue #{ISSUE_NUMBER} from {REPO_FULL_NAME} ...")
    issue = fetch_issue(REPO_FULL_NAME, ISSUE_NUMBER, token)

    print("Cloning repo ...")
    clone_repo(REPO_FULL_NAME, LOCAL_PATH, token)

    print("Indexing repo with tree-sitter ...")
    index = index_repo(LOCAL_PATH)
    relevant_files = get_relevant_files(LOCAL_PATH, issue["body"], index)
    print(f"Relevant files: {relevant_files}")

    initial_state = {
        "issue": issue,
        "repo_path": LOCAL_PATH,
        "relevant_files": relevant_files,
        "max_attempts": MAX_ATTEMPTS,
        "attempt": 0,
    }

    print("Running agent graph (plan -> code -> test -> retry loop) ...")
    app = build_graph()
    final_state = app.invoke(initial_state)

    if final_state["tests_passed"]:
        branch = f"fix/issue-{issue['number']}"
        create_branch_and_commit(LOCAL_PATH, branch, f"Fix: {issue['title']}")
        pr_url = open_pr(
            REPO_FULL_NAME, branch,
            title=f"Fix #{issue['number']}: {issue['title']}",
            body=f"Automated fix.\n\nPlan:\n{final_state['plan']}",
            token=token,
        )
        print(f"Tests passed. PR opened: {pr_url}")
    else:
        print(
            f"Agent could not fix the issue within {MAX_ATTEMPTS} attempts.\n"
            f"Last test output:\n{final_state.get('last_error')}"
        )


if __name__ == "__main__":
    main()
