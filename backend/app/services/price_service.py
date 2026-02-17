"""Historical price fetching service."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict
import httpx
from app.config import settings
from app.utils.errors import PriceServiceError
from app.services.cache_service import CacheService

# Token symbol to CoinGecko ID mapping
TOKEN_MAPPING = {
    "SOL": "solana",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDC": "usd-coin",
    "USDT": "tether",
    "MATIC": "matic-network",
    "AVAX": "avalanche-2",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
}


class PriceService:
    """Service for fetching historical cryptocurrency prices."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.base_url = settings.coingecko_base_url
        self.api_key = settings.coingecko_api_key
        self.cache = cache_service or CacheService()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_coingecko_id(self, token_symbol: str) -> Optional[str]:
        """Get CoinGecko ID from token symbol."""
        return TOKEN_MAPPING.get(token_symbol.upper())
    
    async def get_price(
        self,
        token_symbol: str,
        timestamp: datetime,
        currency: str = "usd"
    ) -> Optional[Decimal]:
        """
        Get historical price for a token at a specific timestamp.
        
        Args:
            token_symbol: Token symbol (e.g., "SOL", "BTC")
            timestamp: Target timestamp
            currency: Target currency (default: "usd")
            
        Returns:
            Price in specified currency, or None if not found
        """
        # Check cache first
        cache_key = self.cache._make_key(
            "price",
            token_symbol.upper(),
            timestamp.isoformat(),
            currency
        )
        cached_price = self.cache.get(cache_key)
        if cached_price is not None:
            return Decimal(str(cached_price))
        
        coingecko_id = self._get_coingecko_id(token_symbol)
        if not coingecko_id:
            # Try using symbol directly (might work for some tokens)
            coingecko_id = token_symbol.lower()
        
        try:
            # CoinGecko historical price endpoint
            # Format: dd-mm-yyyy (e.g., "19-01-2026")
            date_str = timestamp.strftime("%d-%m-%Y")
            url = f"{self.base_url}/coins/{coingecko_id}/history"
            params = {
                "date": date_str,
                "localization": "false"
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            print(f"[PRICE] Fetching price for {token_symbol} on {date_str} (timestamp: {timestamp.isoformat()})")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract price from response
            market_data = data.get("market_data", {})
            if not market_data:
                print(f"[PRICE] WARNING: No market_data in response for {token_symbol} on {date_str}")
                return None
            
            current_price = market_data.get("current_price", {})
            if not current_price:
                print(f"[PRICE] WARNING: No current_price in market_data for {token_symbol} on {date_str}")
                return None
            
            price = current_price.get(currency.lower())
            
            if price is None:
                print(f"[PRICE] WARNING: No {currency} price found for {token_symbol} on {date_str}")
                return None
            
            price_decimal = Decimal(str(price))
            print(f"[PRICE] Found price for {token_symbol}: {price_decimal} {currency.upper()} on {date_str}")
            
            # Cache the result
            self.cache.set(cache_key, str(price_decimal), ttl_seconds=86400)  # Cache for 24 hours
            
            return price_decimal
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Token not found
                return None
            raise PriceServiceError(f"HTTP error fetching price: {e.response.status_code}")
        except httpx.HTTPError as e:
            raise PriceServiceError(f"Error fetching price: {str(e)}")
        except Exception as e:
            raise PriceServiceError(f"Unexpected error: {str(e)}")
    
    async def get_price_batch(
        self,
        token_symbols: list[str],
        timestamp: datetime,
        currency: str = "usd"
    ) -> dict[str, Optional[Decimal]]:
        """
        Get historical prices for multiple tokens at once.
        
        Args:
            token_symbols: List of token symbols
            timestamp: Target timestamp
            currency: Target currency
            
        Returns:
            Dictionary mapping token symbols to prices
        """
        import asyncio
        
        # Fetch prices in parallel using asyncio.gather
        tasks = {
            symbol: self.get_price(symbol, timestamp, currency)
            for symbol in token_symbols
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to symbols
        price_dict = {}
        for (symbol, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                print(f"Error fetching price for {symbol}: {result}")
                price_dict[symbol] = None
            else:
                price_dict[symbol] = result
        
        return price_dict
    
    async def get_current_price(
        self,
        token_symbol: str,
        currency: str = "usd"
    ) -> Optional[Decimal]:
        """
        Get current price for a token.
        
        Args:
            token_symbol: Token symbol
            currency: Target currency
            
        Returns:
            Current price
        """
        return await self.get_price(token_symbol, datetime.utcnow(), currency)
