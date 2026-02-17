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
        duplicates = 0
        for tx in transactions:
            if tx.id not in seen_ids:
                seen_ids.add(tx.id)
                unique_transactions.append(tx)
            else:
                duplicates += 1
                print(f"[NORMALIZE] Duplicate transaction detected: {tx.id} (type: {tx.type}, timestamp: {tx.timestamp})")
        
        if duplicates > 0:
            print(f"[NORMALIZE] Removed {duplicates} duplicate transactions")
        print(f"[NORMALIZE] Total transactions: {len(transactions)}, Unique: {len(unique_transactions)}")
        
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
        
        # Fetch USD prices for token_in
        if tx.token_in and not tx.price_in_usd and tx.amount_in:
            try:
                print(f"[ENRICH] Fetching price for {tx.token_in.symbol} at {tx.timestamp.isoformat()}")
                price_usd = await self.price_service.get_price(
                    tx.token_in.symbol,
                    tx.timestamp
                )
                if price_usd:
                    tx.price_in_usd = price_usd
                    # Calculate total USD value
                    usd_value = tx.amount_in * price_usd
                    print(f"[ENRICH] {tx.token_in.symbol}: {tx.amount_in} * {price_usd} USD = {usd_value} USD")
                    # Convert to EUR
                    eur_value = await self.currency_service.convert(
                        usd_value,
                        "USD",
                        "EUR",
                        tx.timestamp.date()
                    )
                    # Store price per unit in EUR
                    tx.price_in_eur = eur_value / tx.amount_in if tx.amount_in > 0 else Decimal("0")
                    print(f"[ENRICH] {tx.token_in.symbol}: {usd_value} USD -> {eur_value} EUR (price: {tx.price_in_eur} EUR per unit)")
                else:
                    print(f"[ENRICH] WARNING: Could not fetch price for {tx.token_in.symbol} at {tx.timestamp.isoformat()}")
            except Exception as e:
                # Log error but continue
                print(f"[ENRICH] Error fetching price for {tx.token_in.symbol}: {e}")
                import traceback
                traceback.print_exc()
        
        # Fetch USD prices for token_out
        if tx.token_out and not tx.price_out_usd and tx.amount_out:
            try:
                print(f"[ENRICH] Fetching price for {tx.token_out.symbol} at {tx.timestamp.isoformat()}")
                price_usd = await self.price_service.get_price(
                    tx.token_out.symbol,
                    tx.timestamp
                )
                if price_usd:
                    tx.price_out_usd = price_usd
                    # Calculate total USD value
                    usd_value = tx.amount_out * price_usd
                    print(f"[ENRICH] {tx.token_out.symbol}: {tx.amount_out} * {price_usd} USD = {usd_value} USD")
                    # Convert to EUR
                    eur_value = await self.currency_service.convert(
                        usd_value,
                        "USD",
                        "EUR",
                        tx.timestamp.date()
                    )
                    # Store price per unit in EUR
                    tx.price_out_eur = eur_value / tx.amount_out if tx.amount_out > 0 else Decimal("0")
                    print(f"[ENRICH] {tx.token_out.symbol}: {usd_value} USD -> {eur_value} EUR (price: {tx.price_out_eur} EUR per unit)")
                else:
                    print(f"[ENRICH] WARNING: Could not fetch price for {tx.token_out.symbol} at {tx.timestamp.isoformat()}")
            except Exception as e:
                # Log error but continue
                print(f"[ENRICH] Error fetching price for {tx.token_out.symbol}: {e}")
                import traceback
                traceback.print_exc()
        
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
