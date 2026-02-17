"""Currency conversion service."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import httpx
from app.config import settings
from app.utils.errors import CurrencyServiceError
from app.services.cache_service import CacheService


class CurrencyService:
    """Service for currency conversion."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.base_url = settings.exchange_rate_base_url
        self.api_key = settings.exchange_rate_api_key
        self.cache = cache_service or CacheService()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        target_date: date
    ) -> Decimal:
        """
        Get exchange rate between two currencies at a specific date.
        
        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "EUR")
            target_date: Date for exchange rate
            
        Returns:
            Exchange rate
        """
        # Check cache first
        cache_key = self.cache._make_key(
            "fx",
            from_currency.upper(),
            to_currency.upper(),
            target_date.isoformat()
        )
        cached_rate = self.cache.get(cache_key)
        if cached_rate is not None:
            return Decimal(str(cached_rate))
        
        # If same currency, return 1.0
        if from_currency.upper() == to_currency.upper():
            return Decimal("1.0")
        
        try:
            # Use ExchangeRate API (free tier)
            # Format: /v4/historical/{date}
            date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.base_url}/historical/{date_str}"
            
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key
            
            print(f"[FX] Fetching exchange rate {from_currency} -> {to_currency} for {date_str}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            rates = data.get("rates", {})
            if not rates:
                print(f"[FX] WARNING: No rates in response for {date_str}")
                raise CurrencyServiceError(f"No exchange rates available for {date_str}")
            
            from_rate = Decimal(str(rates.get(from_currency.upper(), 1)))
            to_rate = Decimal(str(rates.get(to_currency.upper(), 1)))
            
            if from_rate == 0:
                raise CurrencyServiceError(f"Invalid exchange rate for {from_currency}")
            
            # Calculate rate: to_currency / from_currency
            exchange_rate = to_rate / from_rate
            print(f"[FX] Exchange rate {from_currency} -> {to_currency}: {exchange_rate} on {date_str}")
            
            # Cache the result
            self.cache.set(cache_key, str(exchange_rate), ttl_seconds=86400 * 365)  # Cache for 1 year
            
            return exchange_rate
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try alternative: ECB API for EUR (free, no key required)
                if to_currency.upper() == "EUR":
                    return await self._get_ecb_rate(from_currency, target_date)
            raise CurrencyServiceError(f"HTTP error fetching exchange rate: {e.response.status_code}")
        except httpx.HTTPError as e:
            raise CurrencyServiceError(f"Error fetching exchange rate: {str(e)}")
        except Exception as e:
            raise CurrencyServiceError(f"Unexpected error: {str(e)}")
    
    async def _get_ecb_rate(self, from_currency: str, target_date: date) -> Decimal:
        """
        Get exchange rate from ECB API (European Central Bank).
        
        ECB API provides EUR rates for free, no API key required.
        """
        try:
            # ECB API endpoint
            url = "https://api.exchangerate.host/historical"
            params = {
                "base": "EUR",
                "symbols": from_currency.upper(),
                "date": target_date.strftime("%Y-%m-%d")
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            rates = data.get("rates", {})
            eur_to_currency = Decimal(str(rates.get(from_currency.upper(), 1)))
            
            if eur_to_currency == 0:
                raise CurrencyServiceError(f"Invalid ECB rate for {from_currency}")
            
            # Convert: 1 USD = X EUR means 1 EUR = 1/X USD
            # So if we want USD to EUR: rate = 1 / eur_to_usd
            if from_currency.upper() == "USD":
                return Decimal("1") / eur_to_currency
            else:
                # For other currencies, we need USD as intermediate
                usd_to_eur = await self._get_ecb_rate("USD", target_date)
                currency_to_usd = Decimal("1") / eur_to_currency
                return currency_to_usd * usd_to_eur
                
        except Exception as e:
            raise CurrencyServiceError(f"Error fetching ECB rate: {str(e)}")
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        target_date: date
    ) -> Decimal:
        """
        Convert amount from one currency to another at a specific date.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "EUR")
            target_date: Date for exchange rate
            
        Returns:
            Converted amount
        """
        if amount == 0:
            return Decimal("0")
        
        rate = await self.get_exchange_rate(from_currency, to_currency, target_date)
        return amount * rate
