"""GitHub integration: fetching issues, cloning repos, committing patches,
and opening pull requests.
"""
import os
from github import Github
import git


def fetch_issue(repo_full_name: str, issue_number: int, token: str) -> dict:
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    issue = repo.get_issue(issue_number)
    return {"title": issue.title, "body": issue.body or "", "number": issue.number}


def clone_repo(repo_full_name: str, local_path: str, token: str):
    url = f"https://{token}@github.com/{repo_full_name}.git"
    if os.path.exists(local_path):
        return git.Repo(local_path)
    return git.Repo.clone_from(url, local_path)


def create_branch_and_commit(repo_path: str, branch_name: str, message: str):
    repo = git.Repo(repo_path)
    repo.git.checkout("-b", branch_name)
    repo.git.add(A=True)
    repo.index.commit(message)
    repo.git.push("--set-upstream", "origin", branch_name)


def open_pr(repo_full_name: str, branch_name: str, title: str, body: str, token: str) -> str:
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.create_pull(title=title, body=body, head=branch_name, base="main")
    return pr.html_url
