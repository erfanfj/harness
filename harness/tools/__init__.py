from pathlib import Path
from typing import Callable, Optional
from harness.tools.base import ToolRegistry
from harness.tools.filesystem import FileSystemTools
from harness.tools.terminal import TerminalTools
from harness.tools.memory import MemoryTools


def create_default_registry(
    workspace_dir: Path,
    command_timeout: int = 180,
    on_finish: Optional[Callable[[str, bool], None]] = None,
) -> tuple[ToolRegistry, MemoryTools]:
    """
    Creates and populates a default ToolRegistry with all filesystem,
    terminal, and memory tools configured for the workspace.
    """
    registry = ToolRegistry()
    fs_tools = FileSystemTools(workspace_dir)
    term_tools = TerminalTools(workspace_dir, default_timeout=command_timeout)
    mem_tools = MemoryTools(on_finish=on_finish)

    # 1. write_file
    registry.register(
        name="write_file",
        description="Creates or overwrites a file in the project. Automatically creates any missing parent directories.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute file path to write to.",
                },
                "content": {
                    "type": "string",
                    "description": "The exact full text content to write into the file.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to overwrite existing file if it already exists (default: true).",
                },
            },
            "required": ["path", "content"],
        },
        func=fs_tools.write_file,
    )

    # 2. read_file
    registry.register(
        name="read_file",
        description="Reads content of a file with line numbers (1-indexed). Allows reading specific line ranges.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, default: 1).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (inclusive, default: 300).",
                },
            },
            "required": ["path"],
        },
        func=fs_tools.read_file,
    )

    # 3. replace_in_file
    registry.register(
        name="replace_in_file",
        description="Replaces an exact target snippet with replacement text in a file. Used for precise surgical code edits.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to modify.",
                },
                "target": {
                    "type": "string",
                    "description": "Exact text substring to be replaced (must match exactly, including indentation).",
                },
                "replacement": {
                    "type": "string",
                    "description": "The new replacement text.",
                },
            },
            "required": ["path", "target", "replacement"],
        },
        func=fs_tools.replace_in_file,
    )

    # 4. list_directory
    registry.register(
        name="list_directory",
        description="Lists files and subdirectories in a directory, displaying file sizes and types.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current workspace root '.').",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan subdirectories recursively (default: false).",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth when recursive is true (default: 3).",
                },
            },
            "required": [],
        },
        func=fs_tools.list_directory,
    )

    # 5. search_in_files
    registry.register(
        name="search_in_files",
        description="Searches for a text pattern or regex across files in the project.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The text pattern or regular expression to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Root path to start searching from (default: '.').",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter filenames (e.g. '*.py', '*.json', default: '*').",
                },
            },
            "required": ["query"],
        },
        func=fs_tools.search_in_files,
    )

    # 6. get_project_tree
    registry.register(
        name="get_project_tree",
        description="Generates an ASCII tree view of the workspace project structure.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory to generate tree from (default: '.').",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth of tree (default: 4).",
                },
            },
            "required": [],
        },
        func=fs_tools.get_project_tree,
    )

    # 7. execute_command
    registry.register(
        name="execute_command",
        description="Executes a shell command (pip, npm, pytest, git, python, etc.) in the workspace directory. Captures stdout, stderr, and exit code.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact shell command line string to run.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional timeout in seconds (default: 60). Always specify a short timeout (e.g. 5 to 15s) when executing something that could wait on network or block.",
                },
            },
            "required": ["command"],
        },
        func=term_tools.execute_command,
    )

    # 8. update_plan
    registry.register(
        name="update_plan",
        description="Updates your persistent scratchpad and roadmap to track completed tasks, current focus, and next steps.",
        parameters={
            "type": "object",
            "properties": {
                "scratchpad": {
                    "type": "string",
                    "description": "The markdown-formatted plan, checklist, or scratchpad content.",
                },
            },
            "required": ["scratchpad"],
        },
        func=mem_tools.update_plan,
    )

    # 9. view_plan
    registry.register(
        name="view_plan",
        description="Retrieves the current scratchpad and plan notes.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=mem_tools.view_plan,
    )

    # 10. finish_task
    registry.register(
        name="finish_task",
        description="Signals completion of the entire task when all code is written, dependencies installed, and tests pass. Provide a full final summary.",
        parameters={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Detailed explanation of the completed solution, architecture, files created, and how to run/use the project.",
                },
                "tests_passed": {
                    "type": "boolean",
                    "description": "Whether all automated tests and verifications passed (default: true).",
                },
            },
            "required": ["summary"],
        },
        func=mem_tools.finish_task,
    )

    return registry, mem_tools
