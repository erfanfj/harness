import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


@dataclass
class AgentConfig:
    """Configuration for the AI Harness Agent."""
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_URL", "https://api.deepseek.com"))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "deepseek-chat"))
    workspace_dir: Path = field(default_factory=lambda: Path(os.getenv("WORKSPACE_DIR", os.getcwd())).resolve())
    max_iterations: int = field(default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "60")))
    max_context_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "64000")))
    command_timeout: int = field(default_factory=lambda: int(os.getenv("COMMAND_TIMEOUT", "60")))

    def __post_init__(self):
        if isinstance(self.workspace_dir, str):
            self.workspace_dir = Path(self.workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Normalize base_url (remove trailing slashes)
        self.base_url = self.base_url.rstrip("/")

    def validate(self) -> None:
        """Validates that necessary configuration parameters are present."""
        if not self.api_key or self.api_key.strip() in ("", "your_deepseek_api_key_here"):
            raise ValueError(
                "DEEPSEEK_API_KEY is not set! Please set it in .env, export it in your environment, "
                "or pass it via --api-key."
            )
        if not self.base_url:
            raise ValueError("DEEPSEEK_URL is not set!")
        if not self.model_name:
            raise ValueError("MODEL_NAME is not set!")
