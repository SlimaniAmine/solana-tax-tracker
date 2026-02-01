"""Wallet models."""
from pydantic import BaseModel, Field
from typing import List, Optional


class WalletRequest(BaseModel):
    """Request model for wallet processing."""
    addresses: List[str] = Field(..., min_items=1, max_items=10, description="List of wallet addresses")
    year: Optional[int] = Field(None, description="Filter transactions by year")


class WalletResponse(BaseModel):
    """Response model for wallet processing."""
    addresses: List[str]
    transaction_count: int
    status: str
    message: Optional[str] = None
