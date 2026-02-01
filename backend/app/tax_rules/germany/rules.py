"""German tax rules and regulations."""
from app.tax_rules.base import CostBasisMethod, HoldingPeriodRule

# German tax rules
GERMANY_HOLDING_PERIOD_DAYS = 365  # 1 year
GERMANY_TAX_RATE_SHORT_TERM = 0.0  # Short-term gains are tax-free (if under 600 EUR threshold)
GERMANY_TAX_RATE_LONG_TERM = 0.0  # Long-term gains are tax-free (if under 600 EUR threshold)
GERMANY_TAX_FREE_THRESHOLD_EUR = 600  # Tax-free threshold per year

# Cost basis method: FIFO (First In, First Out)
GERMANY_COST_BASIS_METHOD = CostBasisMethod.FIFO

# Staking rewards are treated as income (not capital gains)
GERMANY_STAKING_AS_INCOME = True

def get_germany_holding_period_rule() -> HoldingPeriodRule:
    """Get holding period rule for Germany."""
    return HoldingPeriodRule(
        days=GERMANY_HOLDING_PERIOD_DAYS,
        tax_rate=GERMANY_TAX_RATE_LONG_TERM
    )
