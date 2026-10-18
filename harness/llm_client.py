import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from harness.config import AgentConfig


@dataclass
class ToolCallItem:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: List[ToolCallItem] = field(default_factory=list)
    raw_message: Optional[Dict[str, Any]] = None


class DeepSeekClient:
    """
    Robust OpenAI-compatible client wrapper for DeepSeek API.
    Handles authentication, tool schemas, retries, and reasoning token extraction.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=120.0,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        retries: int = 3,
    ) -> LLMResponse:
        """
        Sends messages and tools to the DeepSeek API with retry support.
        """
        delay = 2.0
        last_exception = None

        for attempt in range(1, retries + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.config.model_name,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = self.client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                # Extract reasoning content if returned (DeepSeek R1 / reasoner)
                reasoning = getattr(message, "reasoning_content", None)

                # Extract tool calls
                parsed_tool_calls: List[ToolCallItem] = []
                raw_tool_calls = getattr(message, "tool_calls", None)

                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        func_name = tc.function.name
                        func_args_str = tc.function.arguments
                        try:
                            func_args = json.loads(func_args_str) if func_args_str else {}
                        except json.JSONDecodeError:
                            func_args = {"raw_arguments": func_args_str}

                        parsed_tool_calls.append(
                            ToolCallItem(
                                id=tc.id,
                                name=func_name,
                                arguments=func_args,
                            )
                        )

                # Prepare raw dict representation for history
                raw_dict: Dict[str, Any] = {"role": "assistant"}
                content_str = message.content or ""
                if not content_str and not raw_tool_calls:
                    content_str = "Proceeding with next step."
                raw_dict["content"] = content_str

                if raw_tool_calls:
                    raw_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in raw_tool_calls
                    ]

                return LLMResponse(
                    content=message.content,
                    reasoning_content=reasoning,
                    tool_calls=parsed_tool_calls,
                    raw_message=raw_dict,
                )

            except (RateLimitError, APIConnectionError) as e:
                last_exception = e
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
            except APIError as e:
                # If tool_choice is not supported on certain models (e.g. reasoner), fallback gracefully
                if "tool" in str(e).lower() and tools:
                    try:
                        # Fallback without tools if the endpoint completely rejects them
                        kwargs.pop("tools", None)
                        kwargs.pop("tool_choice", None)
                        response = self.client.chat.completions.create(**kwargs)
                        choice = response.choices[0]
                        message = choice.message
                        return LLMResponse(
                            content=message.content,
                            reasoning_content=getattr(message, "reasoning_content", None),
                            tool_calls=[],
                            raw_message={"role": "assistant", "content": message.content},
                        )
                    except Exception:
                        raise e
                raise e
            except Exception as e:
                last_exception = e
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e

        if last_exception:
            raise last_exception
        raise RuntimeError("Failed to complete LLM request after retries.")
