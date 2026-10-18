import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure the root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from harness.config import AgentConfig
from harness.agent import AutonomousAgent
from harness.persian import set_persian_fix
from harness import ui


def parse_args():
    parser = argparse.ArgumentParser(
        description="⚡ AI Harness - Autonomous Coding Agent powered by DeepSeek ⚡",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("DEEPSEEK_API_KEY", ""),
        help="DeepSeek API Key (or set DEEPSEEK_API_KEY in .env)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("DEEPSEEK_URL", "https://api.deepseek.com"),
        help="DeepSeek API Base URL (or set DEEPSEEK_URL in .env)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("MODEL_NAME", "deepseek-chat"),
        help="Model Name (e.g., deepseek-chat, deepseek-reasoner)",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        type=str,
        default=None,
        help="Target folder where the project should be created and tested.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        type=str,
        default=None,
        help="Task prompt for the agent to execute.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=60,
        help="Maximum autonomous ReAct iterations per task.",
    )
    parser.add_argument(
        "--no-persian-fix",
        action="store_true",
        default=False,
        help="Disable automatic Persian/Arabic text reshaping and BiDi reordering.",
    )
    return parser.parse_args()


def interactive_prompt_for_configs(args) -> tuple[str, str, str, Path, str]:
    """Prompts the user interactively for any missing configuration parameters."""
    ui.console.print("\n[bold cyan]=== ⚙ AI Harness Configuration ===[/bold cyan]\n")

    api_key = args.api_key.strip()
    if not api_key:
        api_key = ui.console.input("[bold yellow]Enter DEEPSEEK_API_KEY:[/bold yellow] ").strip()

    base_url = args.url.strip() if args.url else "https://api.deepseek.com"
    if not args.url or args.url == "https://api.deepseek.com":
        custom_url = ui.console.input(f"[bold yellow]Enter DEEPSEEK_URL[/bold yellow] [dim]({base_url})[/dim]: ").strip()
        if custom_url:
            base_url = custom_url

    model_name = args.model.strip() if args.model else "deepseek-chat"
    if not args.model or args.model == "deepseek-chat":
        custom_model = ui.console.input(f"[bold yellow]Enter MODEL_NAME[/bold yellow] [dim]({model_name})[/dim]: ").strip()
        if custom_model:
            model_name = custom_model

    workspace_str = args.workspace
    if not workspace_str:
        default_ws = Path.cwd() / "generated_project"
        custom_ws = ui.console.input(f"[bold yellow]Enter Target Project Path[/bold yellow] [dim]({default_ws})[/dim]: ").strip()
        workspace_path = Path(custom_ws).resolve() if custom_ws else default_ws
    else:
        workspace_path = Path(workspace_str).resolve()

    prompt = args.prompt
    if not prompt:
        ui.console.print("\n[bold green]Enter your project prompt / instructions (Press Enter when done):[/bold green]")
        prompt = ui.console.input("[bold white]> [/bold white]").strip()

    return api_key, base_url, model_name, workspace_path, prompt


def main():
    load_dotenv()
    args = parse_args()
    set_persian_fix(not args.no_persian_fix)

    # If key or prompt is not supplied via CLI or env, gather interactively
    if not args.api_key or not args.prompt or not args.workspace:
        api_key, base_url, model_name, workspace_path, prompt = interactive_prompt_for_configs(args)
    else:
        api_key = args.api_key
        base_url = args.url
        model_name = args.model
        workspace_path = Path(args.workspace).resolve()
        prompt = args.prompt

    if not api_key:
        ui.print_error("Error: DEEPSEEK_API_KEY is required to run the agent!")
        sys.exit(1)

    if not prompt:
        ui.print_error("Error: Prompt cannot be empty!")
        sys.exit(1)

    workspace_path.mkdir(parents=True, exist_ok=True)

    config = AgentConfig(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        workspace_dir=workspace_path,
        max_iterations=args.max_steps,
    )

    try:
        agent = AutonomousAgent(config)
    except Exception as e:
        ui.print_error(f"Initialization Error: {str(e)}")
        sys.exit(1)

    # Execute task
    current_prompt = prompt
    while True:
        agent.run_task(current_prompt)

        # REPL mode for follow-up requests
        ui.console.print("\n[bold cyan]💡 What would you like the agent to do next?[/bold cyan]")
        ui.console.print("[dim]Type your next instructions, or type 'exit' or 'quit' to conclude.[/dim]")
        try:
            next_input = ui.console.input("[bold white]Next task > [/bold white]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not next_input or next_input.lower() in ("exit", "quit", "q"):
            ui.console.print("[bold green]Goodbye! Your project is ready in:[/bold green] " + str(workspace_path))
            break

        current_prompt = next_input


if __name__ == "__main__":
    main()
