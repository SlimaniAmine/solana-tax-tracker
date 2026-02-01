"""Wallet processing endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.wallet import WalletRequest, WalletResponse
from app.config import settings
from app.services.chain_adapters.solana import SolanaAdapter
from app.utils.errors import WalletError

router = APIRouter()


@router.post("/process", response_model=WalletResponse)
async def process_wallets(request: WalletRequest):
    """
    Process transactions from multiple Solana wallet addresses.
    
    This endpoint will:
    1. Fetch all transactions from each wallet
    2. Parse and normalize transactions
    3. Return transaction count and status
    """
    if len(request.addresses) > settings.max_wallets:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_wallets} wallets allowed"
        )
    
    adapter = SolanaAdapter(settings.solana_rpc_url)
    total_transactions = 0
    
    try:
        async with adapter:
            for address in request.addresses:
                try:
                    raw_transactions = await adapter.fetch_transactions(
                        address,
                        limit=settings.max_transactions_per_wallet
                    )
                    total_transactions += len(raw_transactions)
                except WalletError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Error processing wallet {address}: {str(e)}"
                    )
        
        return WalletResponse(
            addresses=request.addresses,
            transaction_count=total_transactions,
            status="success",
            message=f"Processed {len(request.addresses)} wallet(s), found {total_transactions} transactions"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing wallets: {str(e)}"
        )


@router.get("/validate/{address}")
async def validate_wallet(address: str):
    """Validate a Solana wallet address."""
    adapter = SolanaAdapter(settings.solana_rpc_url)
    is_valid = adapter.validate_address(address)
    
    return {
        "address": address,
        "valid": is_valid,
        "message": "Address is valid" if is_valid else "Invalid Solana address format"
    }
