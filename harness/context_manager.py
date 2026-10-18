import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def estimate_tokens(text: str) -> int:
    """Fast approximation of token count (~3.8 characters per token)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


class ContextManager:
    """
    Manages conversational history, token counting, pruning,
    output compaction, schema sanitization, and persistent memory on disk.
    """

    def __init__(self, workspace_dir: Path, max_tokens: int = 64000):
        self.workspace_dir = workspace_dir
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, Any]] = []
        self.memory_dir = workspace_dir / ".agent_memory"
        self.memory_file = self.memory_dir / "memory.json"

    @staticmethod
    def sanitize_message(msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures strict compliance with OpenAI message schemas so proxies/endpoints
        (like vLLM, LiteLLM, Ollama, DeepSeek) never fail Pydantic validation:
        - content is NEVER None (always string)
        - tool_calls is omitted if empty or None
        - assistant messages have valid content or valid tool_calls
        """
        role = msg.get("role", "user")
        clean: Dict[str, Any] = {"role": role}

        if role in ("system", "user"):
            clean["content"] = str(msg.get("content") or "")
            return clean

        elif role == "tool":
            clean["content"] = str(msg.get("content") or "")
            clean["tool_call_id"] = str(msg.get("tool_call_id") or "call_unknown")
            if "name" in msg and msg["name"]:
                clean["name"] = str(msg["name"])
            return clean

        elif role == "assistant":
            content = msg.get("content")
            tool_calls = msg.get("tool_calls")

            # Content must always be a string
            clean["content"] = str(content) if content is not None else ""

            # Validate tool_calls
            if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
                clean_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tc_id = str(tc.get("id") or "call_unknown")
                        func_info = tc.get("function")
                        if isinstance(func_info, dict):
                            func_name = str(func_info.get("name") or "")
                            func_args = str(func_info.get("arguments") or "{}")
                        else:
                            func_name = str(tc.get("name") or "")
                            func_args = str(tc.get("arguments") or "{}")

                        clean_calls.append({
                            "id": tc_id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": func_args,
                            },
                        })
                if clean_calls:
                    clean["tool_calls"] = clean_calls

            # If assistant message has neither tool_calls nor non-empty content,
            # provide a valid non-empty string so proxies never reject it as empty.
            if "tool_calls" not in clean and not clean["content"].strip():
                clean["content"] = "Proceeding with next action."

            return clean

        else:
            clean["content"] = str(msg.get("content") or "")
            return clean

    def add_message(self, message: Dict[str, Any]) -> None:
        """Adds a sanitized message to the conversation history."""
        self.messages.append(self.sanitize_message(message))

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": str(content or "")})

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        msg: Dict[str, Any] = {"role": "assistant"}
        if content is not None:
            msg["content"] = str(content)
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(self.sanitize_message(msg))

    def add_tool_message(self, tool_call_id: str, name: str, content: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": str(tool_call_id),
            "name": str(name),
            "content": str(content or ""),
        })

    def total_estimated_tokens(self) -> int:
        """Computes approximate token count for all current messages."""
        total = 0
        for msg in self.messages:
            content = msg.get("content") or ""
            total += estimate_tokens(str(content))
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                total += estimate_tokens(json.dumps(tool_calls))
        return total

    def prepare_messages_for_llm(self, system_prompt: str) -> List[Dict[str, Any]]:
        """
        Prepares, prunes, and sanitizes messages to fit safely within the LLM context limit.
        Compacts older tool outputs if total tokens exceed 70% of max_tokens.
        """
        # Ensure system prompt is the first message
        prepared: List[Dict[str, Any]] = [{"role": "system", "content": str(system_prompt or "")}]

        current_tokens = self.total_estimated_tokens() + estimate_tokens(system_prompt)
        threshold = int(self.max_tokens * 0.70)

        if current_tokens <= threshold or len(self.messages) <= 12:
            raw_list = prepared + self.messages
        else:
            recent_count = 8
            older_messages = self.messages[:-recent_count]
            recent_messages = self.messages[-recent_count:]

            compacted_older: List[Dict[str, Any]] = []
            for msg in older_messages:
                msg_copy = dict(msg)
                if msg_copy.get("role") == "tool":
                    content = str(msg_copy.get("content", ""))
                    tool_name = msg_copy.get("name", "tool")
                    if len(content) > 300:
                        summary_snippet = content[:150].strip()
                        lines = content.splitlines()
                        msg_copy["content"] = (
                            f"[Historical tool output compacted: {tool_name} returned {len(lines)} lines. "
                            f"Initial excerpt: {summary_snippet}...]"
                        )
                compacted_older.append(msg_copy)

            raw_list = prepared + compacted_older + recent_messages

        # Run full schema sanitization on every single message
        return [self.sanitize_message(m) for m in raw_list]

    def save_memory(self, task_objective: str, scratchpad: str, completed: bool = False) -> None:
        """Persists agent state, plan, and session summary to disk."""
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "workspace": str(self.workspace_dir),
                "last_updated": datetime.now().isoformat(),
                "task_objective": task_objective,
                "scratchpad": scratchpad,
                "completed": completed,
                "message_count": len(self.messages),
                "estimated_tokens": self.total_estimated_tokens(),
            }
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_memory(self) -> Optional[Dict[str, Any]]:
        """Loads persistent memory from disk if available."""
        if not self.memory_file.exists():
            return None
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
