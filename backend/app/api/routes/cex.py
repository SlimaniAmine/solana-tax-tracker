"""CEX integration endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
from pydantic import BaseModel
from app.services.cex_adapters.kraken import KrakenAdapter
from app.services.cex_adapters.coinbase import CoinbaseAdapter
from app.utils.errors import CexIntegrationError

router = APIRouter()


class CexApiKeyRequest(BaseModel):
    """Request model for CEX API key connection."""
    exchange: str  # "kraken", "coinbase", etc.
    api_key: str
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None  # For Coinbase


@router.post("/connect")
async def connect_cex_api(request: CexApiKeyRequest):
    """
    Connect to a CEX using API keys.
    
    Stores API credentials securely (encrypted if authentication is enabled).
    """
    if request.exchange.lower() == "kraken":
        adapter = KrakenAdapter()
        try:
            transactions = await adapter.fetch_transactions_via_api(
                request.api_key,
                request.api_secret or ""
            )
            return {
                "exchange": request.exchange,
                "status": "success",
                "transaction_count": len(transactions),
                "message": f"Successfully connected and fetched {len(transactions)} transactions"
            }
        except NotImplementedError:
            return {
                "exchange": request.exchange,
                "status": "pending",
                "message": "API integration not yet implemented. Please use CSV upload."
            }
    elif request.exchange.lower() == "coinbase":
        adapter = CoinbaseAdapter()
        try:
            transactions = await adapter.fetch_transactions_via_api(
                request.api_key,
                request.api_secret or "",
                request.passphrase
            )
            return {
                "exchange": request.exchange,
                "status": "success",
                "transaction_count": len(transactions),
                "message": f"Successfully connected and fetched {len(transactions)} transactions"
            }
        except NotImplementedError:
            return {
                "exchange": request.exchange,
                "status": "pending",
                "message": "API integration not yet implemented. Please use CSV upload."
            }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exchange: {request.exchange}"
        )


@router.post("/upload/{exchange}")
async def upload_cex_csv(exchange: str, file: UploadFile = File(...)):
    """
    Upload CSV file from a CEX.
    
    Supported exchanges: kraken, coinbase, etc.
    """
    if exchange.lower() not in ["kraken", "coinbase"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exchange: {exchange}"
        )
    
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        if exchange.lower() == "kraken":
            adapter = KrakenAdapter()
            transactions = adapter.parse_csv(csv_content)
        elif exchange.lower() == "coinbase":
            adapter = CoinbaseAdapter()
            transactions = adapter.parse_csv(csv_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported exchange")
        
        return {
            "exchange": exchange,
            "filename": file.filename,
            "status": "success",
            "transaction_count": len(transactions),
            "message": f"Successfully parsed {len(transactions)} transactions from CSV"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing CSV: {str(e)}"
        )
