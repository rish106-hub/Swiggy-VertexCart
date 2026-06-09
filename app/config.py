from __future__ import annotations
"""
Application configuration.
All values read from environment variables. Fail fast on missing required keys.
PRD ref: Section 8.2 (Technical Stack), Environment Variables Reference
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── LLM ──────────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Swiggy MCP ────────────────────────────────────────────────────────
    swiggy_client_id: str = ""
    swiggy_auth_url: str = "https://accounts.swiggy.com/oauth/authorize"
    swiggy_token_url: str = "https://accounts.swiggy.com/oauth/token"
    swiggy_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"

    swiggy_food_mcp_url: str = "https://mcp.swiggy.com/food"
    swiggy_instamart_mcp_url: str = "https://mcp.swiggy.com/im"
    swiggy_dineout_mcp_url: str = "https://mcp.swiggy.com/dineout"

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql://vertexcart:vertexcart@localhost:5432/vertexcart"

    # ── App ───────────────────────────────────────────────────────────────
    mock_mode: bool = True
    log_session_ids: bool = True
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
