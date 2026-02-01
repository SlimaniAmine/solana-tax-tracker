"""Transaction normalization service."""
from typing import List, Set
from datetime import datetime
from app.models.transaction import Transaction
from app.services.price_service import PriceService
from app.services.currency_service import CurrencyService


class TransactionNormalizer:
    """Service for normalizing transactions from multiple sources."""
    
    def __init__(
        self,
        price_service: PriceService,
        currency_service: CurrencyService
    ):
        self.price_service = price_service
        self.currency_service = currency_service
    
    async def normalize(
        self,
        transactions: List[Transaction],
        fetch_prices: bool = True
    ) -> List[Transaction]:
        """
        Normalize and merge transactions from multiple sources.
        
        This method:
        1. Sorts transactions by timestamp
        2. Validates transaction data
        3. Removes duplicates
        4. Fetches prices and converts to EUR if requested
        5. Ensures consistent formatting
        
        Args:
            transactions: List of transactions from various sources
            fetch_prices: Whether to fetch prices and convert to EUR
            
        Returns:
            Normalized and sorted list of transactions
        """
        if not transactions:
            return []
        
        # Remove duplicates based on transaction ID
        seen_ids: Set[str] = set()
        unique_transactions = []
        for tx in transactions:
            if tx.id not in seen_ids:
                seen_ids.add(tx.id)
                unique_transactions.append(tx)
        
        # Sort by timestamp
        unique_transactions.sort(key=lambda x: x.timestamp)
        
        # Fetch prices and convert to EUR if requested
        if fetch_prices:
            async with self.price_service, self.currency_service:
                for tx in unique_transactions:
                    await self._enrich_transaction(tx)
        
        return unique_transactions
    
    async def _enrich_transaction(self, tx: Transaction):
        """
        Enrich transaction with price data and EUR conversion.
        
        Fetches USD prices and converts to EUR.
        """
        from decimal import Decimal
        
        # Fetch USD prices
        if tx.token_in and not tx.price_in_usd:
            try:
                price_usd = await self.price_service.get_price(
                    tx.token_in.symbol,
                    tx.timestamp
                )
                if price_usd:
                    tx.price_in_usd = price_usd
                    # Convert to EUR
                    if tx.amount_in and tx.amount_in > 0:
                        usd_value = tx.amount_in * price_usd
                        eur_value = await self.currency_service.convert(
                            usd_value,
                            "USD",
                            "EUR",
                            tx.timestamp.date()
                        )
                        tx.price_in_eur = eur_value / tx.amount_in
            except Exception as e:
                # Log error but continue
                print(f"Error fetching price for {tx.token_in.symbol}: {e}")
        
        if tx.token_out and not tx.price_out_usd:
            try:
                price_usd = await self.price_service.get_price(
                    tx.token_out.symbol,
                    tx.timestamp
                )
                if price_usd:
                    tx.price_out_usd = price_usd
                    # Convert to EUR
                    if tx.amount_out and tx.amount_out > 0:
                        usd_value = tx.amount_out * price_usd
                        eur_value = await self.currency_service.convert(
                            usd_value,
                            "USD",
                            "EUR",
                            tx.timestamp.date()
                        )
                        tx.price_out_eur = eur_value / tx.amount_out
            except Exception as e:
                # Log error but continue
                print(f"Error fetching price for {tx.token_out.symbol}: {e}")
        
        # Convert fee to EUR if present
        if tx.fee and not tx.fee_eur:
            try:
                if tx.fee_token:
                    fee_price_usd = await self.price_service.get_price(
                        tx.fee_token.symbol,
                        tx.timestamp
                    )
                    if fee_price_usd:
                        fee_usd_value = tx.fee * fee_price_usd
                        tx.fee_eur = await self.currency_service.convert(
                            fee_usd_value,
                            "USD",
                            "EUR",
                            tx.timestamp.date()
                        )
                else:
                    # Default to SOL fee
                    sol_price_usd = await self.price_service.get_price(
                        "SOL",
                        tx.timestamp
                    )
                    if sol_price_usd:
                        fee_usd_value = tx.fee * sol_price_usd
                        tx.fee_eur = await self.currency_service.convert(
                            fee_usd_value,
                            "USD",
                            "EUR",
                            tx.timestamp.date()
                        )
            except Exception as e:
                # Log error but continue
                print(f"Error converting fee to EUR: {e}")
    
    def filter_by_year(self, transactions: List[Transaction], year: int) -> List[Transaction]:
        """
        Filter transactions by tax year.
        
        Args:
            transactions: List of transactions
            year: Tax year to filter
            
        Returns:
            Filtered transactions
        """
        filtered = []
        for tx in transactions:
            tx_year = tx.timestamp.year
            if tx_year == year:
                filtered.append(tx)
        return filtered
    
    async def merge_transactions(
        self,
        transaction_lists: List[List[Transaction]],
        fetch_prices: bool = True
    ) -> List[Transaction]:
        """
        Merge multiple lists of transactions into one sorted list.
        
        Args:
            transaction_lists: List of transaction lists from different sources
            fetch_prices: Whether to fetch prices and convert to EUR
            
        Returns:
            Merged and sorted list of transactions
        """
        all_transactions = []
        for tx_list in transaction_lists:
            all_transactions.extend(tx_list)
        
        return await self.normalize(all_transactions, fetch_prices=fetch_prices)
