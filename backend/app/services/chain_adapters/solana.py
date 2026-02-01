"""Solana chain adapter."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import httpx
import base58
import asyncio
from app.services.chain_adapters.base import ChainAdapter, RawTransaction
from app.models.transaction import Transaction, TransactionType, Token
from app.utils.errors import WalletError

# Solana native token
SOL_TOKEN = Token(
    symbol="SOL",
    name="Solana",
    address="So11111111111111111111111111111111111112",
    decimals=9,
    chain="solana"
)


class SolanaAdapter(ChainAdapter):
    """Adapter for Solana blockchain."""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _rpc_call(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Make RPC call to Solana."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            response = await self.client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise WalletError(f"RPC error: {data['error'].get('message', 'Unknown error')}")
            
            return data.get("result")
        except httpx.HTTPError as e:
            raise WalletError(f"HTTP error calling Solana RPC: {str(e)}")
    
    async def fetch_transactions(self, address: str, limit: int = 1000) -> List[RawTransaction]:
        """
        Fetch transactions from Solana RPC.
        
        Uses getSignaturesForAddress to get transaction signatures,
        then fetches full transaction details.
        """
        if not self.validate_address(address):
            raise WalletError(f"Invalid Solana address: {address}")
        
        # Get transaction signatures
        signatures_result = await self._rpc_call(
            "getSignaturesForAddress",
            [
                address,
                {
                    "limit": min(limit, 1000)  # Solana RPC limit
                }
            ]
        )
        
        if not signatures_result:
            return []
        
        signatures = [sig["signature"] for sig in signatures_result]
        
        # Fetch full transaction details in batches
        transactions = []
        batch_size = 10  # Fetch 10 transactions at a time
        
        for i in range(0, len(signatures), batch_size):
            batch = signatures[i:i + batch_size]
            
            # Fetch transactions in parallel
            tasks = [
                self._rpc_call("getTransaction", [
                    sig,
                    {
                        "encoding": "jsonParsed",
                        "maxSupportedTransactionVersion": 0
                    }
                ])
                for sig in batch
            ]
            
            # Execute in parallel using asyncio.gather
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        # Log error but continue with other transactions
                        print(f"Error fetching transaction: {result}")
                        continue
                    if result:
                        transactions.append(RawTransaction(result))
            except Exception as e:
                # Log error but continue with other batches
                print(f"Error processing batch: {e}")
                continue
        
        return transactions
    
    def parse_transaction(self, raw_tx: RawTransaction) -> List[Transaction]:
        """
        Parse Solana transaction into normalized Transaction objects.
        
        Handles:
        - Transfers (SOL and SPL tokens)
        - Swaps (DEX transactions)
        - Staking rewards
        """
        tx_data = raw_tx.data
        if not tx_data:
            return []
        
        transactions = []
        
        # Extract transaction metadata
        signature = tx_data.get("transaction", {}).get("signatures", [""])[0]
        block_time = tx_data.get("blockTime")
        if not block_time:
            return []  # Skip if no timestamp
        
        timestamp = datetime.fromtimestamp(block_time)
        
        # Parse transaction message
        message = tx_data.get("transaction", {}).get("message", {})
        account_keys = message.get("accountKeys", [])
        
        # Get transaction fee
        meta = tx_data.get("meta", {})
        fee = Decimal(str(meta.get("fee", 0))) / Decimal("1000000000")  # Convert lamports to SOL
        
        # Check for staking rewards
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        
        # Detect staking rewards (balance increase without corresponding transfer)
        for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
            if post > pre:
                balance_change = (post - pre) / 1e9  # Convert lamports to SOL
                if balance_change > 0.001:  # Minimum threshold for staking reward
                    # Check if this is a staking reward (not a transfer)
                    # Staking rewards typically come from system program
                    reward_info = meta.get("rewards", [])
                    for reward in reward_info:
                        if reward.get("pubkey") == account_keys[i].get("pubkey"):
                            transactions.append(Transaction(
                                id=f"{signature}_reward_{i}",
                                timestamp=timestamp,
                                type=TransactionType.STAKE_REWARD,
                                chain="solana",
                                source="wallet",
                                token_out=SOL_TOKEN,
                                amount_out=Decimal(str(balance_change)),
                                fee=Decimal("0"),
                                raw_data=tx_data,
                                audit_notes=f"Staking reward detected from balance change"
                            ))
                            break
        
        # Parse token transfers
        pre_token_balances = meta.get("preTokenBalances", [])
        post_token_balances = meta.get("postTokenBalances", [])
        
        # Build token balance map
        token_balance_changes: Dict[str, Dict[str, Decimal]] = {}
        
        for balance in pre_token_balances:
            owner = balance.get("owner", "")
            mint = balance.get("mint", "")
            amount = Decimal(str(balance.get("uiTokenAmount", {}).get("uiAmount", 0)))
            key = f"{owner}_{mint}"
            if key not in token_balance_changes:
                token_balance_changes[key] = {"pre": Decimal("0"), "post": Decimal("0")}
            token_balance_changes[key]["pre"] = amount
        
        for balance in post_token_balances:
            owner = balance.get("owner", "")
            mint = balance.get("mint", "")
            amount = Decimal(str(balance.get("uiTokenAmount", {}).get("uiAmount", 0)))
            key = f"{owner}_{mint}"
            if key not in token_balance_changes:
                token_balance_changes[key] = {"pre": Decimal("0"), "post": Decimal("0")}
            token_balance_changes[key]["post"] = amount
        
        # Create transactions for token balance changes
        for key, changes in token_balance_changes.items():
            diff = changes["post"] - changes["pre"]
            if abs(diff) > Decimal("0.000001"):  # Minimum threshold
                owner, mint = key.split("_", 1)
                decimals = 9  # Default, should be fetched from token metadata
                
                # Try to get decimals from token balance info
                for balance in post_token_balances:
                    if balance.get("owner") == owner and balance.get("mint") == mint:
                        decimals = balance.get("uiTokenAmount", {}).get("decimals", 9)
                        break
                
                token = Token(
                    symbol=mint[:8],  # Simplified - should fetch from token registry
                    name=mint,
                    address=mint,
                    decimals=decimals,
                    chain="solana"
                )
                
                if diff > 0:
                    # Token received
                    transactions.append(Transaction(
                        id=f"{signature}_token_in_{len(transactions)}",
                        timestamp=timestamp,
                        type=TransactionType.TRANSFER,
                        chain="solana",
                        source="wallet",
                        token_out=token,
                        amount_out=diff,
                        fee=fee if len(transactions) == 0 else Decimal("0"),
                        raw_data=tx_data,
                        audit_notes=f"Token transfer detected"
                    ))
                else:
                    # Token sent
                    transactions.append(Transaction(
                        id=f"{signature}_token_out_{len(transactions)}",
                        timestamp=timestamp,
                        type=TransactionType.TRANSFER,
                        chain="solana",
                        source="wallet",
                        token_in=token,
                        amount_in=abs(diff),
                        fee=fee if len(transactions) == 0 else Decimal("0"),
                        raw_data=tx_data,
                        audit_notes=f"Token transfer detected"
                    ))
        
        # Parse SOL transfers
        if pre_balances and post_balances:
            for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                diff = (post - pre) / 1e9
                if abs(diff) > Decimal("0.000001") and diff != fee:  # Exclude fee
                    if diff > 0:
                        # SOL received
                        transactions.append(Transaction(
                            id=f"{signature}_sol_in_{i}",
                            timestamp=timestamp,
                            type=TransactionType.TRANSFER,
                            chain="solana",
                            source="wallet",
                            token_out=SOL_TOKEN,
                            amount_out=Decimal(str(diff)),
                            fee=Decimal("0"),
                            raw_data=tx_data,
                            audit_notes=f"SOL transfer detected"
                        ))
                    else:
                        # SOL sent
                        transactions.append(Transaction(
                            id=f"{signature}_sol_out_{i}",
                            timestamp=timestamp,
                            type=TransactionType.TRANSFER,
                            chain="solana",
                            source="wallet",
                            token_in=SOL_TOKEN,
                            amount_in=Decimal(str(abs(diff))),
                            fee=Decimal("0"),
                            raw_data=tx_data,
                            audit_notes=f"SOL transfer detected"
                        ))
        
        # Detect swaps (multiple token transfers in same transaction)
        if len(transactions) >= 2:
            # Group transactions and mark swaps
            token_ins = [t for t in transactions if t.token_in]
            token_outs = [t for t in transactions if t.token_out]
            
            if token_ins and token_outs:
                # This might be a swap
                for tx in transactions:
                    if tx.type == TransactionType.TRANSFER:
                        tx.type = TransactionType.SWAP
        
        # If no transactions were created, create a generic one
        if not transactions:
            transactions.append(Transaction(
                id=signature,
                timestamp=timestamp,
                type=TransactionType.TRANSFER,
                chain="solana",
                source="wallet",
                fee=fee,
                raw_data=tx_data,
                audit_notes="Transaction parsed but no clear transfer detected"
            ))
        
        return transactions
    
    def validate_address(self, address: str) -> bool:
        """
        Validate Solana address format.
        
        Solana addresses are base58 encoded, typically 32-44 characters.
        """
        if not address or len(address) < 32 or len(address) > 44:
            return False
        
        try:
            # Try to decode as base58
            decoded = base58.b58decode(address)
            # Solana addresses are 32 bytes
            return len(decoded) == 32
        except Exception:
            return False
