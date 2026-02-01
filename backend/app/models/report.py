"""Report models."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.transaction import Transaction


class TaxSummary(BaseModel):
    """Tax summary for a given period."""
    total_gains_eur: Decimal = Field(default=Decimal("0"), description="Total gains in EUR")
    total_losses_eur: Decimal = Field(default=Decimal("0"), description="Total losses in EUR")
    net_gain_loss_eur: Decimal = Field(default=Decimal("0"), description="Net gain/loss in EUR")
    staking_rewards_eur: Decimal = Field(default=Decimal("0"), description="Total staking rewards in EUR")
    taxable_amount_eur: Decimal = Field(default=Decimal("0"), description="Taxable amount in EUR")
    transaction_count: int = Field(default=0, description="Number of transactions")
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class TaxReport(BaseModel):
    """Complete tax report."""
    country: str = Field(..., description="Country code")
    year: int = Field(..., description="Tax year")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    summary: TaxSummary = Field(..., description="Tax summary")
    transactions: List[Transaction] = Field(default_factory=list, description="Detailed transactions")
    audit_trail: Optional[str] = Field(None, description="Audit trail information")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
