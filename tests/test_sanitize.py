import unittest
from pathlib import Path
from pydantic import TypeAdapter
from openai.types.chat import ChatCompletionMessageParam
from harness.context_manager import ContextManager


class TestMessageSanitization(unittest.TestCase):

    def setUp(self):
        self.cm = ContextManager(Path("."))
        self.type_adapter = TypeAdapter(ChatCompletionMessageParam)

    def test_sanitize_none_content_assistant(self):
        # Exact error case from user's custom proxy:
        # role: assistant with content: None and tool_calls: None
        bad_msg = {"role": "assistant", "content": None, "tool_calls": None, "tool_call_id": None}
        cleaned = self.cm.sanitize_message(bad_msg)

        # Must have string content and no None fields
        self.assertIsInstance(cleaned["content"], str)
        self.assertTrue(len(cleaned["content"]) > 0)
        self.assertNotIn("tool_calls", cleaned)

        # Must pass OpenAI ChatCompletionMessageParam validation without error
        validated = self.type_adapter.validate_python(cleaned)
        self.assertIsNotNone(validated)

    def test_sanitize_assistant_with_tool_calls(self):
        msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "execute_command", "arguments": '{"command": "pytest"}'},
                }
            ],
        }
        cleaned = self.cm.sanitize_message(msg)
        self.assertEqual(cleaned["content"], "")
        self.assertIn("tool_calls", cleaned)
        self.assertEqual(len(cleaned["tool_calls"]), 1)

        validated = self.type_adapter.validate_python(cleaned)
        self.assertIsNotNone(validated)

    def test_sanitize_tool_message(self):
        tool_msg = {"role": "tool", "content": None, "tool_call_id": "call_123"}
        cleaned = self.cm.sanitize_message(tool_msg)
        self.assertEqual(cleaned["content"], "")
        self.assertEqual(cleaned["tool_call_id"], "call_123")

        validated = self.type_adapter.validate_python(cleaned)
        self.assertIsNotNone(validated)

    def test_prepare_messages_all_clean(self):
        self.cm.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": None, "tool_calls": None},
            {"role": "tool", "content": "Output", "tool_call_id": "c1"},
        ]
        prepared = self.cm.prepare_messages_for_llm("System prompt")
        for m in prepared:
            validated = self.type_adapter.validate_python(m)
            self.assertIsNotNone(validated)
            self.assertIsNotNone(m.get("content"))


if __name__ == "__main__":
    unittest.main()
