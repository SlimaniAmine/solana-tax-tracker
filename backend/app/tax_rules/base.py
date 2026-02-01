"""Abstract base class for tax rule engines."""
from abc import ABC, abstractmethod
from typing import List
from enum import Enum
from app.models.transaction import Transaction
from app.models.report import TaxReport


class CostBasisMethod(str, Enum):
    """Cost basis calculation methods."""
    FIFO = "FIFO"  # First In, First Out
    LIFO = "LIFO"  # Last In, First Out
    HIFO = "HIFO"  # Highest In, First Out
    AVERAGE = "AVERAGE"  # Average cost basis


class HoldingPeriodRule:
    """Holding period rule configuration."""
    def __init__(self, days: int, tax_rate: float):
        self.days = days
        self.tax_rate = tax_rate


class TaxRuleEngine(ABC):
    """Abstract base class for country-specific tax rule engines."""
    
    @abstractmethod
    def calculate_tax(self, transactions: List[Transaction], year: int) -> TaxReport:
        """
        Calculate taxes for a list of transactions.
        
        Args:
            transactions: List of normalized transactions
            year: Tax year
            
        Returns:
            Complete tax report
        """
        pass
    
    @abstractmethod
    def get_holding_period_rule(self) -> HoldingPeriodRule:
        """Get holding period rule for this country."""
        pass
    
    @abstractmethod
    def get_cost_basis_method(self) -> CostBasisMethod:
        """Get cost basis calculation method for this country."""
        pass
    
    @abstractmethod
    def get_country_code(self) -> str:
        """Get country code (e.g., 'DE' for Germany)."""
        pass
