from typing import Optional, Callable


class MemoryTools:
    """Provides tools for memory management, planning scratchpad, and task termination."""

    def __init__(self, on_finish: Optional[Callable[[str, bool], None]] = None):
        self.scratchpad: str = ""
        self.is_finished: bool = False
        self.final_summary: str = ""
        self.tests_passed: bool = True
        self.on_finish = on_finish

    def update_plan(self, scratchpad: str) -> str:
        """
        Updates your persistent scratchpad, roadmap, and checklist.
        Use this to keep track of phases, completed steps, pending tasks, and discovered issues.
        """
        self.scratchpad = scratchpad.strip()
        return "Scratchpad and plan updated successfully."

    def view_plan(self) -> str:
        """Views the current scratchpad and plan."""
        if not self.scratchpad:
            return "Scratchpad is currently empty."
        return f"Current Scratchpad:\n{self.scratchpad}"

    def finish_task(self, summary: str, tests_passed: bool = True) -> str:
        """
        Signals that the task has been fully accomplished, dependencies installed,
        code written, tests executed, and all verifications passed.
        Provide a detailed summary of what was accomplished and how to run it.
        """
        self.is_finished = True
        self.final_summary = summary.strip()
        self.tests_passed = tests_passed

        if self.on_finish:
            self.on_finish(self.final_summary, self.tests_passed)

        return "Task marked as finished. The session will now conclude."
