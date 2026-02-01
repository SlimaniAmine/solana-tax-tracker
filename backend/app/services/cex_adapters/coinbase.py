"""Coinbase CEX adapter."""
from typing import List
from datetime import datetime
from decimal import Decimal
import csv
from io import StringIO
from app.services.cex_adapters.base import CexAdapter
from app.models.transaction import Transaction, TransactionType, Token

# Common tokens
SOL_TOKEN = Token(symbol="SOL", name="Solana", address="SOL", decimals=9, chain="solana")
BTC_TOKEN = Token(symbol="BTC", name="Bitcoin", address="BTC", decimals=8, chain="bitcoin")
ETH_TOKEN = Token(symbol="ETH", name="Ethereum", address="ETH", decimals=18, chain="ethereum")
USD_TOKEN = Token(symbol="USD", name="US Dollar", address="USD", decimals=2, chain="fiat")
EUR_TOKEN = Token(symbol="EUR", name="Euro", address="EUR", decimals=2, chain="fiat")


class CoinbaseAdapter(CexAdapter):
    """Adapter for Coinbase exchange."""
    
    TOKEN_MAP = {
        "SOL": SOL_TOKEN,
        "BTC": BTC_TOKEN,
        "ETH": ETH_TOKEN,
        "USD": USD_TOKEN,
        "EUR": EUR_TOKEN,
        "USDT": Token(symbol="USDT", name="Tether", address="USDT", decimals=6, chain="ethereum"),
        "USDC": Token(symbol="USDC", name="USD Coin", address="USDC", decimals=6, chain="ethereum"),
    }
    
    async def fetch_transactions_via_api(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str = None
    ) -> List[Transaction]:
        """Fetch transactions from Coinbase API."""
        # TODO: Implement Coinbase API integration
        # Coinbase uses HMAC-SHA256 authentication
        raise NotImplementedError("Coinbase API integration not yet implemented")
    
    def parse_csv(self, csv_content: str) -> List[Transaction]:
        """
        Parse Coinbase CSV export.
        
        Coinbase CSV format (Transactions):
        - Timestamp, Transaction Type, Asset, Quantity Transacted, Spot Price Currency, 
          Spot Price at Transaction, Subtotal, Total (inclusive of fees), Fees, Notes
        """
        transactions = []
        reader = csv.DictReader(StringIO(csv_content))
        
        for row in reader:
            try:
                # Parse timestamp
                timestamp_str = row.get("Timestamp", "")
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
                
                # Get transaction details
                tx_type_str = row.get("Transaction Type", "").lower()
                asset = row.get("Asset", "")
                quantity = Decimal(str(row.get("Quantity Transacted", 0)))
                spot_price = Decimal(str(row.get("Spot Price at Transaction", 0)))
                total = Decimal(str(row.get("Total (inclusive of fees)", 0)))
                fees = Decimal(str(row.get("Fees", 0)))
                
                # Map asset to token
                token = self.TOKEN_MAP.get(asset, Token(
                    symbol=asset,
                    name=asset,
                    address=asset,
                    decimals=8,
                    chain="coinbase"
                ))
                
                # Determine transaction type
                transaction_type = TransactionType.TRANSFER
                if "buy" in tx_type_str or "receive" in tx_type_str:
                    transaction_type = TransactionType.BUY
                elif "sell" in tx_type_str or "send" in tx_type_str:
                    transaction_type = TransactionType.SELL
                elif "convert" in tx_type_str:
                    transaction_type = TransactionType.SWAP
                
                # Create transaction
                # For buys: we receive crypto, pay USD
                # For sells: we send crypto, receive USD
                if transaction_type == TransactionType.BUY:
                    tx = Transaction(
                        id=f"coinbase_{timestamp.timestamp()}_{len(transactions)}",
                        timestamp=timestamp,
                        type=transaction_type,
                        chain="coinbase",
                        source="coinbase",
                        token_in=USD_TOKEN,
                        token_out=token,
                        amount_in=total,
                        amount_out=quantity,
                        price_in_usd=Decimal("1"),  # USD
                        price_out_usd=spot_price,
                        fee=abs(fees),
                        fee_token=USD_TOKEN if fees > 0 else None,
                        raw_data=row,
                        audit_notes=f"Coinbase CSV import: {tx_type_str}"
                    )
                elif transaction_type == TransactionType.SELL:
                    tx = Transaction(
                        id=f"coinbase_{timestamp.timestamp()}_{len(transactions)}",
                        timestamp=timestamp,
                        type=transaction_type,
                        chain="coinbase",
                        source="coinbase",
                        token_in=token,
                        token_out=USD_TOKEN,
                        amount_in=quantity,
                        amount_out=total - abs(fees),  # Total minus fees
                        price_in_usd=spot_price,
                        price_out_usd=Decimal("1"),  # USD
                        fee=abs(fees),
                        fee_token=USD_TOKEN if fees > 0 else None,
                        raw_data=row,
                        audit_notes=f"Coinbase CSV import: {tx_type_str}"
                    )
                else:
                    # Generic transaction
                    tx = Transaction(
                        id=f"coinbase_{timestamp.timestamp()}_{len(transactions)}",
                        timestamp=timestamp,
                        type=transaction_type,
                        chain="coinbase",
                        source="coinbase",
                        token_out=token if quantity > 0 else None,
                        token_in=token if quantity < 0 else None,
                        amount_out=abs(quantity) if quantity > 0 else None,
                        amount_in=abs(quantity) if quantity < 0 else None,
                        fee=abs(fees) if fees > 0 else None,
                        fee_token=USD_TOKEN if fees > 0 else None,
                        raw_data=row,
                        audit_notes=f"Coinbase CSV import: {tx_type_str}"
                    )
                
                transactions.append(tx)
            except Exception as e:
                # Log error but continue
                print(f"Error parsing Coinbase CSV row: {e}")
                continue
        
        return transactions
    
    def get_supported_csv_formats(self) -> List[str]:
        """Return supported CSV format versions."""
        return ["transactions", "fills"]
