"""Application configuration and settings management."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    """Typed settings loaded from environment variables."""

    app_name: str = Field(default="Onchain Credit Scoring")
    environment: str = Field(
        default=os.getenv("ENVIRONMENT", "local"), description="Deployment stage"
    )
    etherscan_api_key: str = Field(..., description="Etherscan API key")
    openrouter_api_key: Optional[str] = Field(
        default=os.getenv("OPENROUTER_API_KEY"), description="OpenRouter API key"
    )
    openrouter_model: str = Field(
        default=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    )
    llm_provider: str = Field(default=os.getenv("LLM_PROVIDER", "bedrock"))
    bedrock_model_id: str = Field(
        default=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
    )
    bedrock_region: str = Field(default=os.getenv("BEDROCK_REGION", "ap-southeast-2"))
    aws_bearer_token: Optional[str] = Field(
        default=os.getenv("AWS_BEARER_TOKEN_BEDROCK"), description="AWS bearer token"
    )
    template_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "templates",
        description="Templates directory path",
    )
    static_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "static",
        description="Static assets directory path",
    )
    prompts_dir: Path = Field(
        default=Path(__file__).resolve().parents[2] / "prompts",
        description="Prompt templates directory",
    )

    class Config:
        frozen = True


def _get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"{var_name} environment variable is required")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    try:
        return Settings(etherscan_api_key=_get_required_env("ETHERSCAN_API_KEY"))
    except ValidationError as exc:
        raise RuntimeError(f"Invalid application settings: {exc}") from exc
