
import sys
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import main


def read_content(path):
    """Return file text from read_file without the 'Lines X-Y of N:' header."""
    result = main.read_file(path)
    return result.split("\n", 1)[1] if result.startswith("Lines ") else result


def test_add():
    assert main.add(15, 27) == 42


def test_add_negative_numbers():
    assert main.add(-5, -3) == -8


def test_add_zero():
    assert main.add(10, 0) == 10


def test_list_empty_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    assert main.list_files(".") == "The directory is empty."


def test_list_files(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "example.txt").write_text("Hello", encoding="utf-8")
    (tmp_path / "folder").mkdir()

    result = main.list_files(".")

    assert "example.txt" in result
    assert "folder" in result


def test_list_missing_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.list_files("missing")
    assert "error" in result.lower()


def test_write_and_read_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.write_file("test.txt", "Hello MCP")

    assert "successfully" in result.lower()
    assert read_content("test.txt") == "Hello MCP"


def test_write_overwrites_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "Original")
    main.write_file("test.txt", "Updated")
    assert read_content("test.txt") == "Updated"


def test_write_creates_parent_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("folder/nested/test.txt", "Nested")
    assert read_content("folder/nested/test.txt") == "Nested"


def test_read_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.read_file("missing.txt")
    assert "error" in result.lower()


def test_read_directory_instead_of_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "folder").mkdir()
    result = main.read_file("folder")
    assert "error" in result.lower()


def test_search_files_finds_matching_text(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "search_test.md").write_text(
        "# MCP Search Test\nThe search tool is working.\n",
        encoding="utf-8",
    )

    result = main.search_files("working")

    assert "search_test.md:2" in result
    assert "The search tool is working." in result


def test_search_files_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "case_test.txt").write_text(
        "Search TOOL works.\n",
        encoding="utf-8",
    )

    result = main.search_files("search tool")
    assert "case_test.txt:1" in result


def test_search_files_returns_no_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "empty_match.txt").write_text(
        "Nothing relevant here.\n",
        encoding="utf-8",
    )

    assert main.search_files("not present") == "No matches found."


def test_replace_text(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "Hello World")
    result = main.replace_in_file("test.txt", "Hello", "Welcome")

    assert "successful" in result.lower()
    assert read_content("test.txt") == "Welcome World"


def test_replace_all_occurrences(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "cat cat cat")
    result = main.replace_in_file(
        "test.txt", "cat", "dog", replace_all=True
    )

    assert "3" in result
    assert read_content("test.txt") == "dog dog dog"


def test_replace_only_first_occurrence_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "cat cat cat")
    main.replace_in_file("test.txt", "cat", "dog")
    assert read_content("test.txt") == "dog cat cat"


def test_replace_missing_text(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "Hello World")
    result = main.replace_in_file("test.txt", "Missing", "New")

    assert "no matching text" in result.lower()
    assert read_content("test.txt") == "Hello World"


def test_replace_empty_search_text(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "Hello")
    result = main.replace_in_file("test.txt", "", "New")

    assert "cannot be empty" in result.lower()
    assert read_content("test.txt") == "Hello"


def test_replace_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.replace_in_file("missing.txt", "old", "new")
    assert "error" in result.lower()


def test_delete_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    main.write_file("test.txt", "Delete me")
    result = main.delete_file("test.txt", confirm=True)

    assert "successfully" in result.lower()
    assert not (tmp_path / "test.txt").exists()


def test_delete_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.delete_file("missing.txt")
    assert "error" in result.lower()


def test_delete_directory_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "folder").mkdir()
    result = main.delete_file("folder", confirm=True)

    assert "error" in result.lower()
    assert (tmp_path / "folder").is_dir()


@pytest.mark.parametrize(
    "path",
    [
        "../main.py",
        "../../outside.txt",
        "folder/../../outside.txt",
    ],
)
def test_reject_path_traversal(path):
    with pytest.raises(ValueError):
        main.safe_path(path)


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Windows\win.ini",
        r"C:\outside.txt",
    ],
)
def test_reject_absolute_windows_paths(path):
    with pytest.raises(ValueError):
        main.safe_path(path)


def test_reject_absolute_posix_path():
    with pytest.raises(ValueError):
        main.safe_path("/etc/passwd")


def test_reject_traversal_for_all_file_tools():
    assert "error" in main.list_files("..").lower()
    assert "error" in main.read_file("../main.py").lower()
    assert "error" in main.write_file("../outside_test.txt", "blocked").lower()
    assert "error" in main.replace_in_file(
        "../main.py", "old", "new"
    ).lower()
    assert "error" in main.delete_file("../outside_test.txt", confirm=True).lower()


def test_traversal_write_does_not_create_outside_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.write_file("../outside_test.txt", "blocked")

    assert "error" in result.lower()
    assert not (tmp_path.parent / "outside_test.txt").exists()


def test_workspace_root_cannot_be_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.delete_file(".", confirm=True)

    assert "error" in result.lower()
    assert tmp_path.exists()


def test_workspace_root_cannot_be_written_as_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    result = main.write_file(".", "blocked")

    assert "error" in result.lower()
    assert tmp_path.is_dir()


@pytest.mark.parametrize(
    "operation",
    ["write", "replace", "delete"],
)
def test_log_file_is_protected(tmp_path, monkeypatch, operation):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    log_file = tmp_path / "mcp_server.log"
    log_file.write_text("preserve this log", encoding="utf-8")

    if operation == "write":
        result = main.write_file("mcp_server.log", "overwrite")
    elif operation == "replace":
        result = main.replace_in_file(
            "mcp_server.log", "preserve", "replace"
        )
    else:
        result = main.delete_file("mcp_server.log", confirm=True)

    assert "error" in result.lower()
    assert log_file.read_text(encoding="utf-8") == "preserve this log"


def test_internal_symlink_escape_is_rejected(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")

    link = workspace / "external"

    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this environment")

    monkeypatch.setattr(main, "WORKSPACE", workspace)

    with pytest.raises(ValueError):
        main.safe_path("external/secret.txt")

    for operation in (
        lambda: main.read_file("external/secret.txt"),
        lambda: main.write_file("external/new.txt", "blocked"),
        lambda: main.replace_in_file("external/secret.txt", "secret", "changed"),
        lambda: main.delete_file("external/secret.txt", confirm=True),
    ):
        result = operation()
        assert "error" in result.lower()

    assert (outside / "secret.txt").read_text(encoding="utf-8") == "secret"
    assert not (outside / "new.txt").exists()


def test_git_status():
    result = main.git_status()

    assert isinstance(result, str)
    assert result.strip()
    assert "git error" not in result.lower()


def test_git_diff():
    result = main.git_diff()

    assert isinstance(result, str)
    assert "git error" not in result.lower()


def test_git_diff_shows_tracked_changes(tmp_path, monkeypatch):
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_file = tmp_path / "sample.txt"
    tracked_file.write_text("original content\n", encoding="utf-8")

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "sample.txt"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "Initial test commit"],
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_file.write_text("modified content\n", encoding="utf-8")

    result = subprocess.run(
        ["git", "-C", str(tmp_path), "diff", "--", "."],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "original content" in result.stdout
    assert "modified content" in result.stdout


def test_read_file_offset_and_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "lines.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    assert main.read_file("lines.txt", offset=1, limit=2) == "Lines 2-3 of 4:\ntwo\nthree"


@pytest.mark.parametrize("offset,limit", [(-1, 1), (0, 0), (0, 1001)])
def test_read_file_rejects_invalid_bounds(tmp_path, monkeypatch, offset, limit):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "lines.txt").write_text("one\ntwo", encoding="utf-8")
    assert "error" in main.read_file("lines.txt", offset=offset, limit=limit).lower()


def test_search_files_respects_max_results(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    (tmp_path / "many.txt").write_text("needle\nneedle\nneedle\n", encoding="utf-8")
    result = main.search_files("needle", max_results=2)
    assert result.count("needle") == 2
    assert "Result limit reached: 2" in result


def test_search_files_rejects_invalid_max_results(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    assert "error" in main.search_files("needle", max_results=0).lower()
    assert "error" in main.search_files("needle", max_results=501).lower()


def test_delete_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "WORKSPACE", tmp_path)
    target = tmp_path / "keep.txt"
    target.write_text("keep", encoding="utf-8")
    result = main.delete_file("keep.txt")
    assert "confirm=true" in result.lower()
    assert target.exists()
