"""Kraken CEX adapter."""
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


class KrakenAdapter(CexAdapter):
    """Adapter for Kraken exchange."""
    
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
        """Fetch transactions from Kraken API."""
        # TODO: Implement Kraken API integration
        # Kraken uses HMAC-SHA512 authentication
        raise NotImplementedError("Kraken API integration not yet implemented")
    
    def parse_csv(self, csv_content: str) -> List[Transaction]:
        """
        Parse Kraken CSV export.
        
        Kraken CSV format (Ledgers):
        - txid, refid, time, type, subtype, aclass, asset, amount, fee, balance
        """
        transactions = []
        reader = csv.DictReader(StringIO(csv_content))
        
        for row in reader:
            try:
                # Parse timestamp
                timestamp = datetime.fromtimestamp(float(row.get("time", 0)))
                
                # Get transaction type
                tx_type = row.get("type", "").lower()
                asset = row.get("asset", "")
                amount = Decimal(str(row.get("amount", 0)))
                fee = Decimal(str(row.get("fee", 0)))
                txid = row.get("txid", "")
                
                # Map asset to token
                token = self.TOKEN_MAP.get(asset, Token(
                    symbol=asset,
                    name=asset,
                    address=asset,
                    decimals=8,
                    chain="kraken"
                ))
                
                # Determine transaction type
                transaction_type = TransactionType.TRANSFER
                if tx_type in ["deposit", "withdrawal"]:
                    transaction_type = TransactionType.DEPOSIT if tx_type == "deposit" else TransactionType.WITHDRAWAL
                elif tx_type in ["trade", "spend", "receive"]:
                    transaction_type = TransactionType.SWAP if tx_type == "trade" else TransactionType.TRANSFER
                
                # Create transaction
                tx = Transaction(
                    id=f"kraken_{txid}_{len(transactions)}",
                    timestamp=timestamp,
                    type=transaction_type,
                    chain="kraken",
                    source="kraken",
                    token_in=token if amount < 0 else None,
                    token_out=token if amount > 0 else None,
                    amount_in=abs(amount) if amount < 0 else None,
                    amount_out=abs(amount) if amount > 0 else None,
                    fee=abs(fee) if fee > 0 else None,
                    fee_token=token if fee > 0 else None,
                    raw_data=row,
                    audit_notes=f"Kraken CSV import: {tx_type}"
                )
                
                transactions.append(tx)
            except Exception as e:
                # Log error but continue
                print(f"Error parsing Kraken CSV row: {e}")
                continue
        
        return transactions
    
    def get_supported_csv_formats(self) -> List[str]:
        """Return supported CSV format versions."""
        return ["ledgers", "trades"]
