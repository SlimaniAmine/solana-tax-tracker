"""Unified transaction model."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    SWAP = "SWAP"
    TRANSFER = "TRANSFER"
    STAKE_REWARD = "STAKE_REWARD"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class Token(BaseModel):
    """Token information model."""
    symbol: str
    name: str
    address: str
    decimals: int
    chain: str = "solana"


class Transaction(BaseModel):
    """Unified transaction model for all sources."""
    id: str = Field(..., description="Unique transaction identifier")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    type: TransactionType = Field(..., description="Type of transaction")
    chain: str = Field(default="solana", description="Blockchain network")
    source: str = Field(..., description="Source: wallet, kraken, coinbase, etc.")
    
    # Token details
    token_in: Optional[Token] = Field(None, description="Input token")
    token_out: Optional[Token] = Field(None, description="Output token")
    amount_in: Optional[Decimal] = Field(None, description="Input amount")
    amount_out: Optional[Decimal] = Field(None, description="Output amount")
    
    # Pricing (filled by price service)
    price_in_usd: Optional[Decimal] = Field(None, description="Input token price in USD")
    price_out_usd: Optional[Decimal] = Field(None, description="Output token price in USD")
    price_in_eur: Optional[Decimal] = Field(None, description="Input token price in EUR")
    price_out_eur: Optional[Decimal] = Field(None, description="Output token price in EUR")
    
    # Tax calculation fields (filled by tax engine)
    cost_basis_eur: Optional[Decimal] = Field(None, description="Cost basis in EUR")
    proceeds_eur: Optional[Decimal] = Field(None, description="Proceeds in EUR")
    gain_loss_eur: Optional[Decimal] = Field(None, description="Gain/loss in EUR")
    holding_period_days: Optional[int] = Field(None, description="Holding period in days")
    
    # Additional metadata
    fee: Optional[Decimal] = Field(None, description="Transaction fee")
    fee_token: Optional[Token] = Field(None, description="Token used for fee")
    fee_eur: Optional[Decimal] = Field(None, description="Fee in EUR")
    
    # Audit trail
    raw_data: Optional[dict] = Field(None, description="Original raw transaction data")
    audit_notes: Optional[str] = Field(None, description="Notes for audit purposes")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
