from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent


class Settings(BaseSettings):
    data_dir: str = str(PROJECT_ROOT / "data")

    # Comparison-text generation (see synthesis.py). GLM is the default,
    # matching mutercim/fundraising-assistant's free-tier pattern - Ollama
    # is the fallback if GLM fails or no key is set, never the other way
    # around, since this text is public/SEO-facing and GLM's instruction
    # following on "write N words synthesizing these numbers" is more
    # reliable than the local 7B model.
    synthesis_provider: str = "glm"
    glm_api_key: str | None = None
    glm_model: str = "glm-4.5-flash"
    glm_base_url: str = "https://api.z.ai/api/paas/v4/"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    # UN Comtrade: works key-less (500 records/call limit) - only set this
    # if you've registered for a free key and want the higher 100k-record
    # limit (still 500 calls/day either way).
    comtrade_api_key: str | None = None
    wto_api_key: str | None = None

    # Gates POST /api/admin/rebuild - same shape as fundraising-assistant/
    # job-suche's ADMIN_USERNAME/ADMIN_PASSWORD gating, but this is a
    # single bearer token since there's no human login flow here, just a
    # manual "re-run the build after I fixed a SIPRI parse" trigger.
    admin_token: str | None = None

    # Astro's own canonical-URL base (astro.config.mjs reads this too) -
    # empty is fine for local dev, must be the real domain before the SEO
    # layer (schema.org, sitemap, canonical tags) means anything in prod.
    site_url: str = ""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), extra="ignore"
    )


settings = Settings()


def data_dir() -> Path:
    p = Path(settings.data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "global_monitor.sqlite3"


def frontend_dir() -> Path:
    return REPO_ROOT / "frontend"
