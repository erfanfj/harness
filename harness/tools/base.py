import json
import inspect
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Any]

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool definition to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Manages registration, schema generation, and safe execution of tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
    ) -> None:
        """Register a tool."""
        self._tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
        )

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools as OpenAI tool definitions."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any] | str) -> str:
        """Executes a tool with parsed arguments and catches any runtime errors."""
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available tools: {', '.join(self._tools.keys())}"

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except Exception as e:
                return f"Error parsing arguments JSON for tool '{name}': {str(e)}"

        try:
            result = tool.func(**arguments)
            if not isinstance(result, str):
                result = str(result)
            return result
        except TypeError as e:
            sig = inspect.signature(tool.func)
            return f"Error executing tool '{name}': invalid arguments {arguments}. Expected signature: {name}{sig}. Detail: {str(e)}"
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
