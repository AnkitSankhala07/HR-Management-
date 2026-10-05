import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class Settings:
    _base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _sqlite_path = os.path.join(_base_dir, "backend", "db.sqlite3").replace("\\", "/")
    _use_sqlite = (
        os.getenv("DATABASE_ENGINE", "").lower() in ("sqlite", "sqlite3")
        or os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")
    )
    _default_url = (
        f"sqlite:///{_sqlite_path}"
        if _use_sqlite
        else "mysql+pymysql://{u}:{p}@{h}:{port}/{n}?charset=utf8mb4".format(
            u=os.getenv("DATABASE_USER", "dayflow"), p=os.getenv("DATABASE_PASSWORD", ""), h=os.getenv("DATABASE_HOST", "127.0.0.1"),
            port=os.getenv("DATABASE_PORT", "3306"), n=os.getenv("DATABASE_NAME", "dayflow_hrms"))
    )
    database_url: str = os.getenv("FASTAPI_DATABASE_URL") or _default_url
    jwt_secret: str = os.getenv("SERVICE_JWT_SECRET") or os.getenv("SECRET_KEY", "dev-insecure-change-me")
    cors_origins: list[str] = [o for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8000").split(",") if o]
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "claude-sonnet-5-5")


settings = Settings()
