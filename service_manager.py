
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

SERVICES = [
    ("MCP server", "http_server.py", 8000, "mcp_server.log"),
    ("Authentication proxy", "proxy_server.py", 8001, "authentication_proxy.log"),
]

children = {}


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_service(name, script, port, log_name):
    if port_in_use(port):
        print(
            f"ERROR: Port {port} is already occupied. "
            f"Refusing to start a duplicate {name}.",
            flush=True,
        )
        return None

    log_path = ROOT / log_name
    log_file = open(log_path, "a", encoding="utf-8")

    try:
        process = subprocess.Popen(
            [str(PYTHON), str(ROOT / script)],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    finally:
        log_file.close()

    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(
                f"ERROR: {name} exited with code {process.returncode}. "
                f"Check {log_name}.",
                flush=True,
            )
            return None

        if port_in_use(port):
            print(
                f"Started {name} (PID {process.pid}); "
                f"port {port} is listening.",
                flush=True,
            )
            return process

        time.sleep(0.25)

    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    print(
        f"ERROR: {name} did not start on port {port}. "
        f"Check {log_name}.",
        flush=True,
    )
    return None


def stop_services():
    for name, process in list(children.items()):
        if process.poll() is None:
            print(f"Stopping {name}...", flush=True)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    children.clear()


def main():
    if not PYTHON.is_file():
        raise SystemExit(f"Python environment not found: {PYTHON}")

    if not (ROOT / ".mcp-token").is_file():
        raise SystemExit("Missing .mcp-token. No services were started.")

    os.environ["MCP_ACCESS_TOKEN"] = (
        ROOT / ".mcp-token"
    ).read_text(encoding="utf-8").strip()

    if not os.environ["MCP_ACCESS_TOKEN"]:
        raise SystemExit(".mcp-token is empty. No services were started.")

    try:
        for service in SERVICES:
            name, script, port, log_name = service
            process = start_service(name, script, port, log_name)

            if process is None:
                stop_services()
                raise SystemExit(1)

            children[name] = process

        print(
            "Both services are managed. Press Ctrl+C to stop them.",
            flush=True,
        )

        while True:
            for name, script, port, log_name in SERVICES:
                process = children.get(name)

                if process is not None and process.poll() is not None:
                    print(
                        f"{name} exited with code {process.returncode}. "
                        "Restarting in 2 seconds...",
                        flush=True,
                    )
                    time.sleep(2)

                    replacement = start_service(
                        name, script, port, log_name
                    )

                    if replacement is None:
                        print(
                            f"{name} could not restart. "
                            "Will retry in 5 seconds.",
                            flush=True,
                        )
                        time.sleep(5)
                    else:
                        children[name] = replacement

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutdown requested.", flush=True)
    finally:
        stop_services()


if __name__ == "__main__":
    main()
