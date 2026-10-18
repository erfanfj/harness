import os
import re
from pathlib import Path
from typing import Dict, Any, List

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    ".agent_memory",
}


class FileSystemTools:
    """Provides safe filesystem tools scoped to a target workspace directory."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir.resolve()

    def _resolve_path(self, path_str: str) -> Path:
        """Resolves relative or absolute path to an absolute path within workspace."""
        path = Path(path_str)
        if not path.is_absolute():
            resolved = (self.workspace_dir / path).resolve()
        else:
            resolved = path.resolve()
        return resolved

    def write_file(self, path: str, content: str, overwrite: bool = True) -> str:
        """
        Creates or overwrites a file with the given content.
        Parent directories are created automatically.
        """
        target = self._resolve_path(path)
        if target.exists() and not overwrite:
            return f"Error: File '{target}' already exists and overwrite is False."

        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        line_count = len(content.splitlines())
        size_bytes = target.stat().st_size
        rel_path = (
            target.relative_to(self.workspace_dir)
            if target.is_relative_to(self.workspace_dir)
            else target
        )
        return f"Successfully wrote {line_count} lines ({size_bytes} bytes) to '{rel_path}'."

    def read_file(self, path: str, start_line: int = 1, end_line: int = 300) -> str:
        """
        Reads a file with 1-indexed line numbers.
        Allows specifying line range [start_line, end_line].
        """
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if target.is_dir():
            return f"Error: '{path}' is a directory, not a file."

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

        total_lines = len(lines)
        if total_lines == 0:
            return f"File '{path}' is empty (0 lines)."

        start = max(1, start_line)
        end = min(total_lines, end_line)

        if start > total_lines:
            return f"Error: start_line ({start}) exceeds total lines ({total_lines})."

        numbered_lines = []
        for i in range(start - 1, end):
            line_no = i + 1
            numbered_lines.append(f"{line_no:5d} | {lines[i].rstrip()}")

        header = f"File: {path} (Showing lines {start}-{end} of {total_lines})\n"
        output = header + "\n".join(numbered_lines)

        if end < total_lines:
            output += f"\n... [Remaining {total_lines - end} lines not shown]"

        return output

    def replace_in_file(self, path: str, target: str, replacement: str) -> str:
        """
        Replaces exact target string with replacement string in the specified file.
        This enables surgical code edits.
        """
        target_path = self._resolve_path(path)
        if not target_path.exists():
            return f"Error: File '{path}' does not exist."

        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        count = content.count(target)
        if count == 0:
            return (
                f"Error: Target text not found in '{path}'. "
                f"Ensure exact match including whitespace and indentation."
            )
        if count > 1:
            return (
                f"Warning: Target text found {count} times in '{path}'. "
                f"Please provide more surrounding context to make target unambiguous."
            )

        new_content = content.replace(target, replacement, 1)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        rel_path = (
            target_path.relative_to(self.workspace_dir)
            if target_path.is_relative_to(self.workspace_dir)
            else target_path
        )
        return f"Successfully replaced target in '{rel_path}'."

    def list_directory(self, path: str = ".", recursive: bool = False, max_depth: int = 3) -> str:
        """
        Lists files and subdirectories in the specified directory path.
        """
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: Directory '{path}' does not exist."
        if not target.is_dir():
            return f"Error: '{path}' is a file, not a directory."

        entries: List[str] = []

        def scan(dir_path: Path, current_depth: int):
            if current_depth > max_depth:
                return
            try:
                for item in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    if item.name in IGNORED_DIRS:
                        continue
                    rel = item.relative_to(self.workspace_dir)
                    if item.is_dir():
                        entries.append(f"[DIR]  {rel}/")
                        if recursive:
                            scan(item, current_depth + 1)
                    else:
                        size = item.stat().st_size
                        entries.append(f"[FILE] {rel} ({size} bytes)")
            except PermissionError:
                entries.append(f"[ACCESS DENIED] {dir_path.relative_to(self.workspace_dir)}")

        scan(target, 1)
        if not entries:
            return f"Directory '{path}' is empty."

        return f"Contents of '{path}':\n" + "\n".join(entries)

    def search_in_files(self, query: str, path: str = ".", file_pattern: str = "*") -> str:
        """
        Searches for a text pattern in files within path matching file_pattern.
        """
        root = self._resolve_path(path)
        if not root.exists():
            return f"Error: Path '{path}' does not exist."

        matches = []
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            # Fall back to literal search
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        for current_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                file_path = Path(current_root) / file
                if not file_path.match(file_pattern):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, start=1):
                            if pattern.search(line):
                                rel = file_path.relative_to(self.workspace_dir)
                                matches.append(f"{rel}:{line_idx}: {line.strip()[:150]}")
                                if len(matches) >= 50:
                                    break
                except Exception:
                    continue
                if len(matches) >= 50:
                    break
            if len(matches) >= 50:
                break

        if not matches:
            return f"No matches found for '{query}' in '{path}' matching '{file_pattern}'."

        res = f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)
        if len(matches) >= 50:
            res += "\n... (Results capped at 50 matches)"
        return res

    def get_project_tree(self, path: str = ".", max_depth: int = 4) -> str:
        """Generates a tree view of the project structure."""
        root = self._resolve_path(path)
        if not root.exists():
            return f"Error: Path '{path}' does not exist."

        tree_lines = [f"{root.name}/"]

        def build_tree(dir_path: Path, prefix: str = "", depth: int = 1):
            if depth > max_depth:
                return
            try:
                items = sorted([p for p in dir_path.iterdir() if p.name not in IGNORED_DIRS],
                               key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                return

            total = len(items)
            for idx, item in enumerate(items):
                is_last = idx == total - 1
                connector = "└── " if is_last else "├── "
                child_prefix = "    " if is_last else "│   "

                if item.is_dir():
                    tree_lines.append(f"{prefix}{connector}{item.name}/")
                    build_tree(item, prefix + child_prefix, depth + 1)
                else:
                    tree_lines.append(f"{prefix}{connector}{item.name}")

        build_tree(root)
        return "\n".join(tree_lines)
