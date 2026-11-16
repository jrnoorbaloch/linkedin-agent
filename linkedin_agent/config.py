"""Runtime configuration.

Everything is read from environment variables (or a local .env file) so the
agent can run the same way on a laptop, in Docker, or behind a reverse proxy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(Path.cwd() / ".env")


@dataclass
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LA_DATA_DIR", Path.home() / ".linkedin-agent"))
    )
    host: str = field(default_factory=lambda: os.getenv("LA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("LA_PORT", "8787")))
    base_url: str = field(default_factory=lambda: os.getenv("LA_BASE_URL", ""))
    # Optional token that protects the local REST API (used by the Claude skill / MCP).
    api_token: str = field(default_factory=lambda: os.getenv("LA_API_TOKEN", ""))

    # LinkedIn developer app (https://www.linkedin.com/developers/apps)
    linkedin_client_id: str = field(default_factory=lambda: os.getenv("LINKEDIN_CLIENT_ID", ""))
    linkedin_client_secret: str = field(
        default_factory=lambda: os.getenv("LINKEDIN_CLIENT_SECRET", "")
    )
    linkedin_api_version: str = field(
        default_factory=lambda: os.getenv("LINKEDIN_API_VERSION", "202608")
    )
    # Set to "1" after LinkedIn approves Community Management API for your app.
    linkedin_org_enabled: bool = field(
        default_factory=lambda: os.getenv("LINKEDIN_ORG_ENABLED", "0") == "1"
    )

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.base_url:
            self.base_url = f"http://{self.host if self.host != '0.0.0.0' else 'localhost'}:{self.port}"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "agent.db"

    @property
    def key_path(self) -> Path:
        return self.data_dir / "secret.key"

    @property
    def redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}/auth/linkedin/callback"

    @property
    def linkedin_scopes(self) -> list[str]:
        scopes = ["openid", "profile", "email", "w_member_social"]
        if self.linkedin_org_enabled:
            scopes += ["w_organization_social", "r_organization_social", "rw_organization_admin"]
        return scopes


settings = Settings()
