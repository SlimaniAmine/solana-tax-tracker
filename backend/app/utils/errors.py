"""Custom error classes."""
from typing import Optional


class TaxTrackerError(Exception):
    """Base exception for tax tracker application."""
    pass


class WalletError(TaxTrackerError):
    """Error related to wallet operations."""
    pass


class PriceServiceError(TaxTrackerError):
    """Error related to price fetching."""
    pass


class CurrencyServiceError(TaxTrackerError):
    """Error related to currency conversion."""
    pass


class TaxCalculationError(TaxTrackerError):
    """Error related to tax calculation."""
    pass


class CexIntegrationError(TaxTrackerError):
    """Error related to CEX integration."""
    pass
