"""Abstract base class for chain adapters."""
from abc import ABC, abstractmethod
from typing import List
from app.models.transaction import Transaction


class RawTransaction:
    """Raw transaction data from blockchain."""
    def __init__(self, data: dict):
        self.data = data


class ChainAdapter(ABC):
    """Abstract base class for blockchain adapters."""
    
    @abstractmethod
    async def fetch_transactions(self, address: str, limit: int = 1000) -> List[RawTransaction]:
        """
        Fetch raw transactions from the blockchain.
        
        Args:
            address: Wallet address
            limit: Maximum number of transactions to fetch
            
        Returns:
            List of raw transaction objects
        """
        pass
    
    @abstractmethod
    def parse_transaction(self, raw_tx: RawTransaction) -> List[Transaction]:
        """
        Parse a raw transaction into normalized Transaction objects.
        
        Args:
            raw_tx: Raw transaction from blockchain
            
        Returns:
            List of normalized Transaction objects (can be multiple for swaps)
        """
        pass
    
    @abstractmethod
    def validate_address(self, address: str) -> bool:
        """
        Validate a wallet address format.
        
        Args:
            address: Wallet address to validate
            
        Returns:
            True if address is valid
        """
        pass
