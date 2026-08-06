# Autonomous Coding Agent (SWE-agent style)

An agent that takes a GitHub issue, explores the repo, writes a fix, runs tests in a
sandboxed Docker container, and opens a PR — with a self-verification loop
(run tests -> if fail, diagnose -> retry).

## Architecture

```
GitHub Issue -> Explorer (finds relevant files) -> Planner (writes fix plan)
-> Coder (writes patch) -> Sandbox Test Runner ->
   |-- Pass -> Open PR
   `-- Fail -> Diagnoser (reads error) -> back to Coder (retry, max N times)
```

## Project structure

```
coding-agent/
├── agent/
│   ├── graph.py           # LangGraph orchestration
│   ├── nodes.py           # planner, coder, diagnoser nodes
│   ├── repo_context.py    # tree-sitter based repo indexing
│   ├── sandbox.py         # Docker sandboxed execution
│   └── github_tools.py    # issue fetch + PR creation
├── docker/
│   └── Dockerfile.sandbox
├── main.py
├── requirements.txt
├── .env.example
└── workdir/                # cloned repos land here at runtime (gitignored)
```

## Setup

1. Install Python deps:
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

2. Build the sandbox image:
   ```bash
   docker build -t coding-agent-sandbox:latest -f docker/Dockerfile.sandbox .
   ```

3. Copy `.env.example` to `.env` and fill in:
   - `GROQ_API_KEY` — free tier at https://console.groq.com
   - `GITHUB_TOKEN` — a personal access token with `repo` scope (use a throwaway/test repo first)

4. Load the env vars (or use `python-dotenv` / `source .env` depending on your shell):
   ```bash
   export $(cat .env | xargs)
   ```

5. Edit the target repo + issue number at the top of `main.py`:
   ```python
   REPO_FULL_NAME = "yourname/target-repo"
   ISSUE_NUMBER = 12
   ```
   **Use your own throwaway test repo first.** Don't point this at someone else's
   repo without permission — it will open real PRs.

6. Run it:
   ```bash
   python main.py
   ```

## Safety notes

- The sandbox container runs with `network_disabled=True` and a 512MB memory limit,
  so a bad patch (or a malicious repo) can't reach the network or exhaust the host.
- Always test against a repo you own before pointing this at anything else.
- The `coder_node` LLM call is asked to return strict JSON; wrap real usage with
  more validation before trusting it against a repo you care about.

## What makes this "advanced" for a portfolio/CV

- **Sandboxed execution** — isolated, network-disabled, memory-limited container
- **Self-verification loop** — real diagnose-and-retry cycle via a LangGraph
  conditional edge, not single-shot generation
- **Repo-wide context retrieval** — tree-sitter symbol indexing instead of dumping
  the whole repo into the prompt
- **Real git/GitHub integration** — actual branch creation and PR opening

## Possible extensions

- Parse pytest tracebacks into structured error info (file/line/assertion) instead
  of passing raw logs into the next prompt — makes the retry loop noticeably smarter.
- Swap the naive keyword-based file relevance search in `repo_context.py` for an
  embedding-based search (e.g. sentence-transformers + FAISS).
- Support multi-language repos (currently Python-only via tree-sitter-python).
