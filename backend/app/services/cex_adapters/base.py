"""Abstract base class for CEX adapters."""
from abc import ABC, abstractmethod
from typing import List
from app.models.transaction import Transaction


class CexAdapter(ABC):
    """Abstract base class for CEX adapters."""
    
    @abstractmethod
    async def fetch_transactions_via_api(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str = None
    ) -> List[Transaction]:
        """
        Fetch transactions using CEX API.
        
        Args:
            api_key: API key
            api_secret: API secret
            passphrase: Optional passphrase (for Coinbase)
            
        Returns:
            List of normalized transactions
        """
        pass
    
    @abstractmethod
    def parse_csv(self, csv_content: str) -> List[Transaction]:
        """
        Parse CSV export from CEX.
        
        Args:
            csv_content: CSV file content as string
            
        Returns:
            List of normalized transactions
        """
        pass
    
    @abstractmethod
    def get_supported_csv_formats(self) -> List[str]:
        """Return list of supported CSV format versions."""
        pass
