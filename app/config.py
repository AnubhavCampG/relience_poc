from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://reliance:reliance@localhost:5432/reliance"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    deployment_name: str = "gpt-5.2-chat"
    openai_api_version: str = "2024-12-01-preview"
    sql_max_rows: int = 50
    sql_statement_timeout_ms: int = 10000
    sql_reject_select_star: bool = False
    quotes_dir: str = "runtime/quotes"
    uploads_dir: str = "runtime/uploads"
    pdf_max_chars_in_response: int = 8000
    schema_cache_ttl_seconds: int = 300

    allowed_tables: tuple[str, ...] = (
        "PORTAL_CUSTOMER",
        "MDM_DIM_PRODUCT_MASTER_MV",
        "FCT_INVENTORY_MV",
    )

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def ddl_path(self) -> Path:
        return self.data_dir / "ddl" / "Table-Script.sql"

    @property
    def seed_dir(self) -> Path:
        return self.data_dir / "seed"

    def seed_csv_path(self, table: str) -> Path:
        mapping = {
            "MDM_DIM_PRODUCT_MASTER_MV": "Product.csv",
            "FCT_INVENTORY_MV": "Inventory.csv",
            "PORTAL_CUSTOMER": "Customer-Data.csv",
        }
        filename = mapping.get(table)
        if not filename:
            raise KeyError(f"No seed CSV mapped for table: {table}")
        return self.seed_dir / filename

    @property
    def runtime_dir(self) -> Path:
        return PROJECT_ROOT / "runtime"


@lru_cache
def get_settings() -> Settings:
    return Settings()
