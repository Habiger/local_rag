from functools import lru_cache
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DB_",
        extra="ignore"
    )

    host: str 
    port: str 
    name: str 
    user: str 
    password: str 
    
    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class DoclingConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DOCLING_",
        extra="ignore",
    )
    base_url: AnyHttpUrl


class LlamaCppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LLAMA_",
        extra="ignore",
    )
    base_url: AnyHttpUrl

class Settings(BaseSettings):
    """BaseSettings reads values automatically from `.env` file."""
    db: DBConfig = Field(default_factory=DBConfig)  # type: ignore
    docling: DoclingConfig = Field(default_factory=DoclingConfig)  # type: ignore
    llama: LlamaCppConfig = Field(default_factory=LlamaCppConfig)  # type: ignore


@lru_cache
def get_db_config() -> DBConfig:
    return DBConfig() # type: ignore

@lru_cache
def get_docling_config() -> DoclingConfig:
    return DoclingConfig() # type: ignore

@lru_cache
def get_llamacpp_config() -> LlamaCppConfig:
    return LlamaCppConfig() # type: ignore

@lru_cache
def get_settings() -> Settings:
    return Settings()