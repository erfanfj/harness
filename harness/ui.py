import sys
from typing import Any, Dict
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table

from harness.persian import fix_persian_text, fix_persian_markdown

# Force UTF-8 on Windows console if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


def print_banner(model_name: str, base_url: str, workspace_path: str):
    """Displays startup banner with session parameters."""
    title_text = Text("[*] AI HARNESS - Autonomous Software Engineer [*]", style="bold cyan")
    grid = Table.grid(expand=False, padding=(0, 2))
    grid.add_column(style="bold yellow")
    grid.add_column(style="white")

    grid.add_row("Model:", model_name)
    grid.add_row("API Endpoint:", base_url)
    grid.add_row("Target Workspace:", workspace_path)

    panel = Panel(
        grid,
        title=title_text,
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def print_task_start(prompt: str):
    """Displays the initial user prompt with Persian BiDi support."""
    console.print(f"\n[bold cyan]🎯 Starting Autonomous Task:[/bold cyan] {fix_persian_text(prompt)}\n")


def print_step_header(step_idx: int, max_steps: int):
    """Prints step iteration divider."""
    console.print(f"\n[bold blue]=== Step {step_idx}/{max_steps} ====================================================[/bold blue]")


def print_reasoning(reasoning: str):
    """Displays model reasoning or chain-of-thought with Persian BiDi support."""
    fixed = fix_persian_markdown(reasoning)
    panel = Panel(
        Markdown(fixed),
        title="[bold magenta]>> Agent Reasoning / Thinking[/bold magenta]",
        border_style="magenta",
        padding=(0, 1),
    )
    console.print(panel)


def print_agent_thought(content: str):
    """Displays agent narrative thought or explanation with Persian BiDi support."""
    fixed = fix_persian_markdown(content)
    console.print(Panel(Markdown(fixed), title="[bold green]> Agent Response[/bold green]", border_style="green"))


def print_tool_call(tool_name: str, arguments: Dict[str, Any]):
    """Displays an outgoing tool call."""
    args_summary = []
    for k, v in arguments.items():
        v_str = str(v)
        if len(v_str) > 80:
            v_str = v_str[:77] + "..."
        v_str = fix_persian_text(v_str)
        args_summary.append(f"{k}='{v_str}'")

    summary_str = ", ".join(args_summary)
    console.print(f"[bold yellow]-> Executing Tool:[/bold yellow] [bold white]{tool_name}[/bold white]({summary_str})")


def print_tool_result(tool_name: str, result: str):
    """Displays the result of tool execution."""
    lines = result.splitlines()
    if len(lines) > 25:
        preview = "\n".join(lines[:12]) + f"\n... [{len(lines) - 24} lines hidden] ...\n" + "\n".join(lines[-12:])
    else:
        preview = result

    preview = fix_persian_markdown(preview)
    border_color = "red" if "error" in result.lower() or "failed" in result.lower() else "dim white"
    console.print(
        Panel(
            Text(preview, style="dim white"),
            title=f"[dim]Result of {tool_name}[/dim]",
            border_style=border_color,
            padding=(0, 1),
        )
    )


def print_success_summary(summary: str, tests_passed: bool):
    """Displays final accomplishment panel with Persian BiDi support."""
    status_badge = "[bold green][PASS] ALL TESTS PASSED[/bold green]" if tests_passed else "[bold yellow][!] TASK CONCLUDED[/bold yellow]"
    fixed = fix_persian_markdown(summary)
    panel = Panel(
        Markdown(fixed),
        title=f"[bold green]*** Project Generation Complete - {status_badge} ***[/bold green]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def print_error(msg: str):
    """Displays an error message with Persian BiDi support."""
    fixed = fix_persian_text(msg)
    console.print(Panel(Text(fixed, style="bold red"), title="[bold red]Error[/bold red]", border_style="red"))
