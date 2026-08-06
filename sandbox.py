"""Runs the target repo's test suite inside an isolated, network-disabled
Docker container so agent-generated patches can never touch the host or
the network while being verified.
"""
import os
import docker

client = docker.from_env()

SANDBOX_IMAGE = "coding-agent-sandbox:latest"


def run_tests_in_sandbox(repo_path: str, test_command: str = "pytest -q") -> dict:
    """Runs the test suite inside an isolated container. Returns pass/fail + logs."""
    container = client.containers.run(
        image=SANDBOX_IMAGE,
        command=f"bash -c 'cd /workspace && {test_command}'",
        volumes={os.path.abspath(repo_path): {"bind": "/workspace", "mode": "rw"}},
        working_dir="/workspace",
        detach=True,
        mem_limit="512m",
        network_disabled=True,  # no internet inside sandbox — safety
        auto_remove=False,
    )
    exit_code = container.wait()["StatusCode"]
    logs = container.logs().decode("utf-8", errors="ignore")
    container.remove()
    return {"passed": exit_code == 0, "logs": logs}
