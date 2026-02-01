"""German tax rules module."""
from app.tax_rules.germany.calculator import GermanyTaxCalculator
from app.tax_rules.registry import register_tax_engine

# Register Germany tax engine
register_tax_engine("DE", GermanyTaxCalculator)
