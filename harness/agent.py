import time
from typing import Optional
from rich.status import Status
from harness.config import AgentConfig
from harness.llm_client import DeepSeekClient
from harness.tools import create_default_registry
from harness.context_manager import ContextManager
from harness.prompts import get_system_prompt
from harness import ui


class AutonomousAgent:
    """
    Autonomous Software Engineering Agent loop.
    Executes tasks, plans, creates/modifies files, executes commands,
    runs automated tests, and recovers from errors.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.config.validate()

        self.client = DeepSeekClient(config)
        self.registry, self.memory_tools = create_default_registry(
            workspace_dir=self.config.workspace_dir,
            command_timeout=self.config.command_timeout,
        )
        self.context_mgr = ContextManager(
            workspace_dir=self.config.workspace_dir,
            max_tokens=self.config.max_context_tokens,
        )
        self.task_objective: str = ""

    def run_task(self, prompt: str) -> str:
        """
        Executes a software development task from start to completion.
        """
        self.task_objective = prompt
        self.context_mgr.add_user_message(prompt)
        self.memory_tools.is_finished = False

        ui.print_banner(
            model_name=self.config.model_name,
            base_url=self.config.base_url,
            workspace_path=str(self.config.workspace_dir),
        )

        ui.print_task_start(prompt)

        for iteration in range(1, self.config.max_iterations + 1):
            ui.print_step_header(iteration, self.config.max_iterations)

            # 1. Prepare system prompt and pruned context
            system_prompt = get_system_prompt(
                workspace_dir=self.config.workspace_dir,
                current_scratchpad=self.memory_tools.scratchpad,
            )
            messages = self.context_mgr.prepare_messages_for_llm(system_prompt)
            tools = self.registry.get_openai_tools()

            # 2. Query DeepSeek LLM
            with Status("[bold cyan]DeepSeek is reasoning & generating actions...[/bold cyan]", console=ui.console, spinner="dots"):
                try:
                    response = self.client.chat_completion(messages=messages, tools=tools)
                except Exception as e:
                    ui.print_error(f"LLM API Error: {str(e)}")
                    # Wait briefly and retry next iteration if connection dropped
                    time.sleep(3)
                    continue

            # 3. Handle model reasoning & thoughts
            if response.reasoning_content:
                ui.print_reasoning(response.reasoning_content)

            if response.content:
                ui.print_agent_thought(response.content)

            # Save assistant message into context history
            self.context_mgr.add_message(response.raw_message or {"role": "assistant", "content": response.content})

            # 4. Handle finish_task or tool calls
            if self.memory_tools.is_finished:
                ui.print_success_summary(
                    summary=self.memory_tools.final_summary,
                    tests_passed=self.memory_tools.tests_passed,
                )
                self.context_mgr.save_memory(
                    task_objective=self.task_objective,
                    scratchpad=self.memory_tools.scratchpad,
                    completed=True,
                )
                return self.memory_tools.final_summary

            if not response.tool_calls:
                ui.console.print("[dim italic]Agent provided narrative response without tool actions.[/dim italic]")
                self.context_mgr.add_user_message(
                    "Please proceed with the next concrete step by executing the necessary tool (e.g. write_file, execute_command, or finish_task)."
                )
                continue

            # 5. Execute each requested tool call
            for tool_call in response.tool_calls:
                ui.print_tool_call(tool_call.name, tool_call.arguments)

                # Execute tool
                tool_output = self.registry.execute(tool_call.name, tool_call.arguments)
                ui.print_tool_result(tool_call.name, tool_output)

                # Feed result back to context
                self.context_mgr.add_tool_message(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=tool_output,
                )

                # If tool was finish_task
                if self.memory_tools.is_finished:
                    ui.print_success_summary(
                        summary=self.memory_tools.final_summary,
                        tests_passed=self.memory_tools.tests_passed,
                    )
                    self.context_mgr.save_memory(
                        task_objective=self.task_objective,
                        scratchpad=self.memory_tools.scratchpad,
                        completed=True,
                    )
                    return self.memory_tools.final_summary

            # Save checkpoint after each iteration
            self.context_mgr.save_memory(
                task_objective=self.task_objective,
                scratchpad=self.memory_tools.scratchpad,
                completed=False,
            )

        # Max iterations reached
        msg = f"Task reached maximum allowed iterations ({self.config.max_iterations}) without final finish_task."
        ui.print_error(msg)
        return msg
