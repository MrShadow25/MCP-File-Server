from pathlib import Path
import logging
import os
import subprocess
from functools import wraps

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("Demo")

WORKSPACE = (Path(__file__).resolve().parent / "workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

LOG_FILE = WORKSPACE / "mcp_server.log"

logger = logging.getLogger("mcp_server")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)


def log_operation(tool_name: str):
    """Log tool calls and their outcomes."""

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            logger.info("Tool called: %s", tool_name)

            try:
                result = function(*args, **kwargs)

                if isinstance(result, str) and result.lower().startswith(
                    ("error:", "git error:")
                ):
                    logger.warning("Tool failed: %s", tool_name)
                else:
                    logger.info("Tool completed: %s", tool_name)

                return result
            except Exception:
                logger.exception("Tool raised an exception: %s", tool_name)
                raise

        return wrapper

    return decorator


def safe_path(relative_path: str) -> Path:
    """Resolve a path and prevent access outside the workspace."""
    requested = Path(relative_path)

    if requested.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    resolved = (WORKSPACE / requested).resolve()

    try:
        resolved.relative_to(WORKSPACE.resolve())
    except ValueError:
        raise ValueError("Access denied: path is outside the workspace.")

    return resolved


def safe_file_path(relative_path: str) -> Path:
    """Reject symbolic links and paths outside the workspace."""
    requested = Path(relative_path)

    if requested.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    current = WORKSPACE

    for part in requested.parts:
        if part in ("", "."):
            continue

        current = current / part

        if current.is_symlink():
            raise ValueError("Symbolic links are not allowed.")

    return safe_path(relative_path)


def is_log_file(file_path: Path) -> bool:
    """Identify the operation log using the current workspace."""
    return file_path.resolve() == (WORKSPACE / "mcp_server.log").resolve()


@log_operation("add")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@log_operation("list_files")
def list_files(path: str = ".") -> str:
    """List files and folders inside the workspace."""
    try:
        directory = safe_path(path)

        if not directory.is_dir():
            return "Error: The path is not a directory."

        entries = []

        for item in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if item.is_symlink():
                try:
                    item.resolve().relative_to(WORKSPACE.resolve())
                except (ValueError, OSError):
                    entries.append(f"[BLOCKED LINK] {item.name}")
                    continue

            kind = "DIR" if item.is_dir() else "FILE"
            entries.append(f"[{kind}] {item.name}")

        return "\n".join(entries) if entries else "The directory is empty."

    except (ValueError, OSError) as error:
        return f"Error: {error}"


@log_operation("read_file")
def read_file(path: str, offset: int = 0, limit: int = 200) -> str:
    """Read a bounded chunk of a UTF-8 text file. offset is a zero-based line number; limit is the maximum number of lines."""
    try:
        file_path = safe_file_path(path)

        if is_log_file(file_path):
            return "Error: The operation log cannot be read."

        if not file_path.is_file():
            return "Error: The file does not exist."

        if offset < 0 or limit < 1 or limit > 1000:
            return "Error: offset must be >= 0 and limit must be between 1 and 1000."

        lines = file_path.read_text(encoding="utf-8").splitlines()
        selected = lines[offset:offset + limit]
        if not selected:
            return f"No lines available at offset {offset}. Total lines: {len(lines)}."
        return f"Lines {offset + 1}-{offset + len(selected)} of {len(lines)}:\n" + "\n".join(selected)

    except (ValueError, OSError, UnicodeError) as error:
        return f"Error: {error}"


@log_operation("search_files")
def search_files(query: str, path: str = ".", max_results: int = 50) -> str:
    """Search workspace text files; max_results caps matching lines returned."""
    try:
        directory = safe_path(path)

        if not directory.is_dir():
            return "Error: The specified path is not a directory."

        if not query:
            return "Error: Search text cannot be empty."
        if max_results < 1 or max_results > 500:
            return "Error: max_results must be between 1 and 500."

        matches = []

        for current_dir, dirs, files in os.walk(
            directory, followlinks=False
        ):
            current_path = Path(current_dir)

            dirs[:] = [
                name for name in dirs
                if not (current_path / name).is_symlink()
            ]

            for filename in files:
                file_path = current_path / filename

                if is_log_file(file_path):
                    continue

                if file_path.is_symlink() or not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue

                for line_number, line in enumerate(content.splitlines(), 1):
                    if query.casefold() in line.casefold():
                        relative_path = file_path.relative_to(WORKSPACE)
                        matches.append(
                            f"{relative_path}:{line_number}: {line.strip()}"
                        )
                        if len(matches) >= max_results:
                            return "\n".join(matches) + f"\n[Result limit reached: {max_results}]"

        return "\n".join(matches) if matches else "No matches found."

    except (ValueError, OSError) as error:
        return f"Error: {error}"


@log_operation("write_file")
def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 text file inside the workspace."""
    try:
        file_path = safe_file_path(path)

        if file_path == WORKSPACE.resolve():
            return "Error: A file path is required."

        if is_log_file(file_path):
            return "Error: The operation log cannot be overwritten."

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return f"File written successfully: {path}"

    except (ValueError, OSError, UnicodeError) as error:
        return f"Error: {error}"


@log_operation("replace_in_file")
def replace_in_file(
    path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False,
) -> str:
    """Replace matching text in a workspace file."""
    try:
        file_path = safe_file_path(path)

        if is_log_file(file_path):
            return "Error: The operation log cannot be modified."

        if not file_path.is_file():
            return "Error: The file does not exist."

        if not old_text:
            return "Error: The text to find cannot be empty."

        content = file_path.read_text(encoding="utf-8")

        if old_text not in content:
            return "No matching text was found. The file was not changed."

        count = content.count(old_text) if replace_all else 1

        updated = (
            content.replace(old_text, new_text)
            if replace_all
            else content.replace(old_text, new_text, 1)
        )

        file_path.write_text(updated, encoding="utf-8")

        return f"Replacement successful. Occurrences replaced: {count}"

    except (ValueError, OSError, UnicodeError) as error:
        return f"Error: {error}"


@log_operation("delete_file")
def delete_file(path: str, confirm: bool = False) -> str:
    """Delete a workspace file only when confirm=True; directories cannot be deleted."""
    try:
        if not confirm:
            return "Error: Deletion requires explicit confirmation: set confirm=True."

        file_path = safe_file_path(path)

        if file_path == WORKSPACE.resolve():
            return "Error: The workspace root cannot be deleted."

        if is_log_file(file_path):
            return "Error: The operation log cannot be deleted."

        if not file_path.is_file():
            return "Error: The file does not exist or is not a regular file."

        file_path.unlink()

        return f"File deleted successfully: {path}"

    except (ValueError, OSError) as error:
        return f"Error: {error}"


def run_git(*args: str) -> str:
    """Run a read-only Git command in the project repository."""
    project_root = Path(__file__).resolve().parent

    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return f"Git error: {result.stderr.strip()}"

        return result.stdout.strip() or "No output."

    except (OSError, subprocess.TimeoutExpired) as error:
        return f"Git error: {error}"


@log_operation("git_status")
def git_status() -> str:
    """Show the Git status of the project repository."""
    return run_git("status", "--short", "--branch")


@log_operation("git_diff")
def git_diff() -> str:
    """Show unstaged changes to tracked project files."""
    return run_git("diff", "--", ".")


def register_mcp_tool(function):
    """Expose a tool and convert returned error messages to MCP errors."""

    @wraps(function)
    def adapter(*args, **kwargs):
        result = function(*args, **kwargs)

        if isinstance(result, str) and result.lower().startswith(
            ("error:", "git error:")
        ):
            raise ToolError(result)

        return result

    mcp.tool()(adapter)


for tool_function in (
    add,
    list_files,
    read_file,
    search_files,
    write_file,
    replace_in_file,
    delete_file,
    git_status,
    git_diff,
):
    register_mcp_tool(tool_function)


if __name__ == "__main__":
    mcp.run()