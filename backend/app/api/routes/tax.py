"""Tax calculation endpoints."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.report import TaxReport
from app.services.chain_adapters.solana import SolanaAdapter
from app.services.price_service import PriceService
from app.services.currency_service import CurrencyService
from app.services.transaction_normalizer import TransactionNormalizer
from app.tax_rules.registry import get_tax_engine, list_supported_countries
from app.api.routes.reports import generate_excel_report
from app.config import settings

router = APIRouter()


class TaxCalculationRequest(BaseModel):
    """Request model for tax calculation."""
    country: str = Field(..., description="Country code (e.g., 'DE' for Germany)")
    year: int = Field(..., description="Tax year")
    wallet_addresses: Optional[List[str]] = Field(None, description="Wallet addresses to include")
    include_cex: bool = Field(default=True, description="Include CEX transactions")


@router.post("/calculate")
async def calculate_tax(
    request: TaxCalculationRequest,
    format: str = Query(default="json", description="Response format: json or excel")
):
    """
    Calculate taxes for the given country and year.
    
    This endpoint:
    1. Fetches all transactions (wallets + CEX)
    2. Applies country-specific tax rules
    3. Calculates gains, losses, and taxable amounts
    4. Returns a complete tax report (JSON or Excel)
    """
    try:
        # Get tax engine for country
        tax_engine = get_tax_engine(request.country)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Tax rules for country '{request.country}' not available: {str(e)}"
        )
    
    all_transactions = []
    
    # Fetch wallet transactions
    if request.wallet_addresses:
        adapter = SolanaAdapter(settings.solana_rpc_url)
        async with adapter:
            for address in request.wallet_addresses:
                try:
                    raw_txs = await adapter.fetch_transactions(
                        address,
                        limit=settings.max_transactions_per_wallet
                    )
                    for raw_tx in raw_txs:
                        parsed = adapter.parse_transaction(raw_tx)
                        all_transactions.extend(parsed)
                except Exception as e:
                    # Log error but continue
                    print(f"Error processing wallet {address}: {e}")
    
    # TODO: Fetch CEX transactions if include_cex is True
    # This would require storing CEX transactions from previous uploads
    # For now, we'll process only wallet transactions
    
    # Normalize transactions
    price_service = PriceService()
    currency_service = CurrencyService()
    normalizer = TransactionNormalizer(price_service, currency_service)
    
    async with price_service, currency_service:
        normalized = await normalizer.normalize(all_transactions, fetch_prices=True)
        filtered = normalizer.filter_by_year(normalized, request.year)
    
    # Calculate tax
    report = tax_engine.calculate_tax(filtered, request.year)
    
    # Return Excel if requested
    if format.lower() == "excel":
        excel_file = generate_excel_report(report)
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=tax-report-{request.country}-{request.year}.xlsx"
            }
        )
    
    # Return JSON
    return report


@router.get("/countries")
async def list_countries():
    """List all supported countries."""
    countries = list_supported_countries()
    return {
        "countries": [
            {"code": c["code"], "name": c["name"], "supported": True}
            for c in countries
        ]
    }
