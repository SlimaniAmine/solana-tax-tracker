"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_title: str = "Crypto Tax Tracker API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Solana Configuration
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"  # Only used as fallback
    use_solscan: bool = True  # Use Solscan API as primary method
<<<<<<< Current (Your changes)
    solscan_api_url: str = "https://api.solscan.io"
    solscan_api_key: Optional[str] = None  # Optional API key for higher rate limits
=======
    solscan_api_url: str = "https://pro-api.solscan.io"  # Solscan Pro API base URL
    solscan_api_key: Optional[str] = None  # Required API key for Solscan Pro API
>>>>>>> Incoming (Background Agent changes)
    
    # Price Service Configuration
    coingecko_api_key: Optional[str] = None
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    
    # Currency Conversion Configuration
    exchange_rate_api_key: Optional[str] = None
    exchange_rate_base_url: str = "https://api.exchangerate-api.com/v4"
    
    # Cache Configuration
    cache_ttl_seconds: int = 3600  # 1 hour default
    enable_cache: bool = True
    
    # Database Configuration
    database_url: str = "sqlite:///./tax_tracker.db"
    
    # Application Limits
    max_wallets: int = 10
    max_transactions_per_wallet: int = 10000
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
