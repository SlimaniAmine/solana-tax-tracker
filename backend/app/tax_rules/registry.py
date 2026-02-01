"""Tax rule registry."""
from typing import Dict, Type
from app.tax_rules.base import TaxRuleEngine
from app.utils.errors import TaxCalculationError

# Registry of available tax rule engines
_tax_engines: Dict[str, Type[TaxRuleEngine]] = {}


def register_tax_engine(country_code: str, engine_class: Type[TaxRuleEngine]):
    """Register a tax rule engine for a country."""
    _tax_engines[country_code.upper()] = engine_class


def get_tax_engine(country_code: str) -> TaxRuleEngine:
    """
    Get tax rule engine instance for a country.
    
    Args:
        country_code: Country code (e.g., 'DE')
        
    Returns:
        Tax rule engine instance
        
    Raises:
        TaxCalculationError: If country is not supported
    """
    country_code = country_code.upper()
    if country_code not in _tax_engines:
        raise TaxCalculationError(f"Tax rules for country '{country_code}' not yet implemented")
    
    return _tax_engines[country_code]()


def list_supported_countries() -> list[dict]:
    """List all supported countries."""
    return [
        {"code": code, "name": _get_country_name(code)}
        for code in _tax_engines.keys()
    ]


def _get_country_name(code: str) -> str:
    """Get human-readable country name from code."""
    names = {
        "DE": "Germany",
        "FR": "France",
        "UK": "United Kingdom",
        "US": "United States",
    }
    return names.get(code, code)
