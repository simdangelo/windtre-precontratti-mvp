from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MVP_", extra="ignore")

    app_name: str = "MVP Sintesi & Trasparenze"
    database_url: str = "sqlite:///./data/mvp.db"
    data_dir: Path = Path("data")
    generated_dir: Path = Path("data/generated")
    word_template_path: Path = Path("templates/word/sintesi_fisse_template.docx")


settings = Settings()
