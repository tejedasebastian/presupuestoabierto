from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration for the pipeline."""

    environment: str = "local"
    driver_memory: str = "768m"
    data_dir: str = str(_REPO_ROOT / "data")
    # Quality thresholds (phase 3 uses them; defined once, no magic numbers)
    min_rows: int = 10
    max_parse_error_ratio: float = 0.02
    min_month_coverage: int = 12
    monthly_annual_tolerance: float = 0.01
    low_execution_threshold: float = 60.0
    seed_entities: int = 50
    volume_entities: int = 12_800

    model_config = SettingsConfigDict(
        env_prefix="PRESUPUESTO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def raw_dir(self) -> Path:
        return Path(self.data_dir) / "raw"

    @property
    def medallion_dir(self) -> Path:
        return Path(self.data_dir) / "medallion"


@lru_cache
def get_settings() -> Settings:
    return Settings()
