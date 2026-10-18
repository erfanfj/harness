import os
import shutil
import tempfile
from pathlib import Path
import unittest

from harness.config import AgentConfig
from harness.tools.base import ToolRegistry
from harness.tools.filesystem import FileSystemTools
from harness.tools.terminal import TerminalTools
from harness.tools.memory import MemoryTools
from harness.tools import create_default_registry
from harness.context_manager import ContextManager, estimate_tokens
from harness.prompts import get_system_prompt


class TestAIHarness(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_validation(self):
        # Empty API key should raise error
        cfg = AgentConfig(api_key="", workspace_dir=self.workspace)
        with self.assertRaises(ValueError):
            cfg.validate()

        # Valid config
        cfg_valid = AgentConfig(
            api_key="sk-test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
            workspace_dir=self.workspace,
        )
        cfg_valid.validate()
        self.assertEqual(cfg_valid.base_url, "https://api.deepseek.com")

    def test_filesystem_tools(self):
        fs = FileSystemTools(self.workspace)

        # 1. Write file
        res = fs.write_file("sub/hello.py", "def greet():\n    return 'Hello World'\n")
        self.assertIn("Successfully wrote", res)
        self.assertTrue((self.workspace / "sub/hello.py").exists())

        # 2. Read file
        content = fs.read_file("sub/hello.py", start_line=1, end_line=10)
        self.assertIn("def greet():", content)
        self.assertIn("1 | def greet():", content)

        # 3. Replace in file
        replace_res = fs.replace_in_file("sub/hello.py", "'Hello World'", "'Hello DeepSeek'")
        self.assertIn("Successfully replaced", replace_res)
        updated = fs.read_file("sub/hello.py")
        self.assertIn("'Hello DeepSeek'", updated)

        # 4. List directory
        list_res = fs.list_directory(".", recursive=True)
        self.assertIn("hello.py", list_res)

        # 5. Search in files
        search_res = fs.search_in_files("DeepSeek", path=".")
        self.assertIn("hello.py", search_res)

        # 6. Tree
        tree_res = fs.get_project_tree(".")
        self.assertIn("hello.py", tree_res)

    def test_terminal_tools(self):
        term = TerminalTools(self.workspace)
        # 1. Run a simple echo command
        res = term.execute_command("python -c \"print('Hello from Harness')\"")
        self.assertIn("SUCCESS", res)
        self.assertIn("Hello from Harness", res)

        # 2. Test timeout handling and string timeout coercion
        timeout_res = term.execute_command("python -c \"import time; time.sleep(10)\"", timeout="1")
        self.assertIn("TIMED_OUT", timeout_res)

        # 3. Test non-blocking on interactive prompt (stdin=DEVNULL)
        stdin_res = term.execute_command("python -c \"try: input('prompt')\nexcept EOFError: print('EOF_OK')\"")
        self.assertIn("EOF_OK", stdin_res)

    def test_memory_and_planning(self):
        mem = MemoryTools()
        mem.update_plan("1. [x] Step 1\n2. [ ] Step 2")
        self.assertIn("Step 1", mem.view_plan())

        mem.finish_task("Done with project", tests_passed=True)
        self.assertTrue(mem.is_finished)
        self.assertEqual(mem.final_summary, "Done with project")
        self.assertTrue(mem.tests_passed)

    def test_tool_registry(self):
        registry, mem = create_default_registry(self.workspace)
        openai_tools = registry.get_openai_tools()
        tool_names = [t["function"]["name"] for t in openai_tools]

        self.assertIn("write_file", tool_names)
        self.assertIn("read_file", tool_names)
        self.assertIn("replace_in_file", tool_names)
        self.assertIn("execute_command", tool_names)
        self.assertIn("update_plan", tool_names)
        self.assertIn("finish_task", tool_names)

        # Execute a tool via registry
        result = registry.execute("write_file", {"path": "test.txt", "content": "Sample content"})
        self.assertIn("Successfully wrote", result)
        self.assertTrue((self.workspace / "test.txt").exists())

    def test_context_manager_and_compaction(self):
        cm = ContextManager(self.workspace, max_tokens=500)
        cm.add_user_message("Create an app")
        cm.add_assistant_message("I am starting", tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "execute_command", "arguments": "{}"}}])
        
        # Add a huge tool output
        huge_output = "Line of log\n" * 100
        cm.add_tool_message("call_1", "execute_command", huge_output)

        # Add more messages to exceed threshold
        for i in range(15):
            cm.add_assistant_message(f"Step {i}")
            cm.add_user_message(f"Continue {i}")

        prepared = cm.prepare_messages_for_llm("System prompt")
        self.assertEqual(prepared[0]["role"], "system")
        
        # Ensure memory persistence works
        cm.save_memory("Test task", "My scratchpad", completed=True)
        loaded = cm.load_memory()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["task_objective"], "Test task")
        self.assertEqual(loaded["completed"], True)

    def test_prompts(self):
        prompt = get_system_prompt(self.workspace, current_scratchpad="Checklist")
        self.assertIn(str(self.workspace.as_posix()), prompt)
        self.assertIn("Checklist", prompt)


if __name__ == "__main__":
    unittest.main()
