import subprocess
import time
from pathlib import Path


def kill_port(port: int = 8080) -> None:
    result = subprocess.run(
        ["bash", "-lc", f"lsof -tiTCP:{port} -sTCP:LISTEN"],
        text=True,
        capture_output=True,
    )

    for pid in result.stdout.strip().splitlines():
        subprocess.run(["kill", "-9", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_tmux_session(session_name: str) -> None:
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_process_compose_session(repo_root, session_name: str, filename: str = "process-compose.yml") -> None:
    repo_root = Path(repo_root)
    launch_dir = repo_root / "launch"

    kill_port(8080)
    stop_tmux_session(session_name)
    time.sleep(2)

    cmd = (
        f"cd {launch_dir!s} && "
        f"process-compose -f {filename}"
    )

    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "bash", "-lc", cmd],
        text=True,
        capture_output=True,
        check=True,
    )

    print(f"Started tmux session: {session_name}")