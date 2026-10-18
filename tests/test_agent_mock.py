import tempfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from harness.config import AgentConfig
from harness.agent import AutonomousAgent
from harness.llm_client import LLMResponse, ToolCallItem


class TestAgentEndToEnd(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mock_agent_lifecycle(self):
        config = AgentConfig(
            api_key="mock-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            workspace_dir=self.workspace,
            max_iterations=10,
        )

        agent = AutonomousAgent(config)

        # Mock the DeepSeekClient.chat_completion
        mock_responses = [
            # Turn 1: update plan and list directory
            LLMResponse(
                content="I will start by planning the project.",
                reasoning_content="Let me structure the tasks first.",
                tool_calls=[
                    ToolCallItem(
                        id="call_1",
                        name="update_plan",
                        arguments={"scratchpad": "1. Create calculator module\n2. Run tests"},
                    ),
                    ToolCallItem(
                        id="call_2",
                        name="list_directory",
                        arguments={"path": "."},
                    ),
                ],
            ),
            # Turn 2: write calc.py and execute test
            LLMResponse(
                content="Now I will write the code and verify it.",
                tool_calls=[
                    ToolCallItem(
                        id="call_3",
                        name="write_file",
                        arguments={
                            "path": "calc.py",
                            "content": "def add(a, b):\n    return a + b\n",
                        },
                    ),
                    ToolCallItem(
                        id="call_4",
                        name="execute_command",
                        arguments={"command": "python -c \"import calc; assert calc.add(2, 3) == 5\""},
                    ),
                ],
            ),
            # Turn 3: finish task
            LLMResponse(
                content="Tests passed successfully. Concluding task.",
                tool_calls=[
                    ToolCallItem(
                        id="call_5",
                        name="finish_task",
                        arguments={
                            "summary": "Calculator module implemented and verified with assertion test.",
                            "tests_passed": True,
                        },
                    )
                ],
            ),
        ]

        agent.client.chat_completion = MagicMock(side_effect=mock_responses)

        # Run task
        summary = agent.run_task("Build a simple calculator module in Python")

        # Verify outcomes
        self.assertEqual(summary, "Calculator module implemented and verified with assertion test.")
        self.assertTrue((self.workspace / "calc.py").exists())
        self.assertTrue((self.workspace / ".agent_memory" / "memory.json").exists())

        # Verify memory content
        memory = agent.context_mgr.load_memory()
        self.assertIsNotNone(memory)
        self.assertTrue(memory["completed"])
        self.assertIn("calculator module", memory["scratchpad"].lower())


if __name__ == "__main__":
    unittest.main()
