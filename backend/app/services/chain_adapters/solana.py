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
    
    # Common Solana token addresses (mint address -> symbol)
    KNOWN_TOKENS = {
        "So11111111111111111111111111111111111112": "SOL",
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
        "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT": "UXD",
        "A9mUU4qviSctJVPJdBJWkb28deg915LYXErz6kqYxYdk": "USDCet",
        "Dn4noZ5jgGfkntzcQvZR8c47bReYJk5XxKJgx7Wf1Z2h": "USDTet",
    }
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_token_symbol(self, mint_address: str) -> str:
        """Get token symbol from mint address."""
        # Check known tokens first
        if mint_address in self.KNOWN_TOKENS:
            return self.KNOWN_TOKENS[mint_address]
        
        # For unknown tokens, use first 8 chars of address as identifier
        # In production, you'd query a token registry or on-chain metadata
        return mint_address[:8].upper()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _rpc_call(self, method: str, params: List[Any], retries: int = 3) -> Dict[str, Any]:
        """Make RPC call to Solana with retry logic for rate limiting."""
        import asyncio
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        for attempt in range(retries):
            try:
                response = await self.client.post(self.rpc_url, json=payload)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                        print(f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{retries}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise WalletError("Solana RPC rate limit exceeded. Please try again later or use a private RPC endpoint.")
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data['error'].get('message', 'Unknown error')
                    # Don't retry on client errors (4xx), only on server errors (5xx)
                    if data['error'].get('code', 0) >= -32000:  # Client error range
                        raise WalletError(f"RPC error: {error_msg}")
                    # Retry on server errors
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 1
                        await asyncio.sleep(wait_time)
                        continue
                    raise WalletError(f"RPC error: {error_msg}")
                
                return data.get("result")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{retries}")
                    await asyncio.sleep(wait_time)
                    continue
                raise WalletError(f"HTTP error calling Solana RPC: {str(e)}")
            except httpx.HTTPError as e:
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 1
                    await asyncio.sleep(wait_time)
                    continue
                raise WalletError(f"HTTP error calling Solana RPC: {str(e)}")
        
        raise WalletError("Failed to call Solana RPC after retries")
    
    async def fetch_transactions(self, address: str, limit: int = 1000) -> List[RawTransaction]:
        """
        Fetch transactions from Solana using Solscan API.
        
        Primary method: Solscan API (better indexing, more reliable)
        Fallback: Solana RPC (only if Solscan fails)
        """
        if not self.validate_address(address):
            raise WalletError(f"Invalid Solana address: {address}")
        
        from app.config import settings
        
        # PRIMARY METHOD: Use Solscan API
        if settings.use_solscan:
            try:
                print(f"[SOLSCAN] Fetching transactions from Solscan API for {address}...")
                result = await self._fetch_from_solscan(address, limit)
                if result and len(result) > 0:
                    print(f"[SOLSCAN] Successfully fetched {len(result)} transactions from Solscan")
                    return result
                else:
                    print(f"[SOLSCAN] Solscan returned empty result, trying RPC fallback...")
            except Exception as e:
                print(f"[SOLSCAN] Solscan API failed: {e}")
                import traceback
                traceback.print_exc()
                print(f"[SOLSCAN] Falling back to Solana RPC...")
        
        # FALLBACK: Use RPC only if Solscan is disabled or fails
        print(f"[RPC] Using Solana RPC as fallback method...")
        return await self._fetch_from_rpc(address, limit)
    
    async def _fetch_from_solscan(self, address: str, limit: int) -> List[RawTransaction]:
        """Fetch transactions using Solscan Pro API - PRIMARY METHOD."""
        from app.config import settings
        
        # Check if API key is provided (required for Solscan Pro API)
        if not settings.solscan_api_key:
            print(f"[SOLSCAN] No API key provided. Solscan Pro API requires authentication.")
            print(f"[SOLSCAN] Falling back to RPC method...")
            return []
        
        transactions = []
        before = None  # Use 'before' parameter for pagination (signature of last transaction)
        # Solscan Pro API allows limit values: 10, 20, 30, 40
        page_size = 40  # Use max allowed limit
        
        print(f"[SOLSCAN] Fetching transactions from Solscan Pro API for {address}...")
        print(f"[SOLSCAN]   API URL: {settings.solscan_api_url}")
        print(f"[SOLSCAN]   Target limit: {limit} transactions")
        
        while len(transactions) < limit:
            # Solscan Pro API v2.0 endpoint
            url = f"{settings.solscan_api_url}/v2.0/account/transactions"
            
            # Calculate limit for this request (must be 10, 20, 30, or 40)
            remaining = limit - len(transactions)
            request_limit = min(page_size, remaining)
            # Round down to nearest allowed value
            if request_limit > 30:
                request_limit = 40
            elif request_limit > 20:
                request_limit = 30
            elif request_limit > 10:
                request_limit = 20
            else:
                request_limit = 10
            
            params = {
                "address": address,  # Note: parameter is 'address', not 'account'
                "limit": request_limit
            }
            if before:
                params["before"] = before
            
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json",
                "token": settings.solscan_api_key  # Required authentication header
            }
            
            try:
                print(f"[SOLSCAN]   Requesting: {url}")
                print(f"[SOLSCAN]   Params: address={address}, limit={request_limit}, before={before[:16] if before else 'None'}...")
                
                response = await self.client.get(url, params=params, headers=headers, timeout=30.0)
                
                print(f"[SOLSCAN]   Response status: {response.status_code}")
                
                if response.status_code == 401:
                    print(f"[SOLSCAN]   Authentication failed (401). Check your API key.")
                    print(f"[SOLSCAN]   Response: {response.text[:200]}")
                    break
                elif response.status_code == 429:
                    print(f"[SOLSCAN]   Rate limited (429), waiting 5 seconds...")
                    await asyncio.sleep(5)
                    continue
                elif response.status_code != 200:
                    print(f"[SOLSCAN]   HTTP error {response.status_code}: {response.text[:200]}")
                    break
                
                data = response.json()
                print(f"[SOLSCAN]   Response type: {type(data)}")
                
                # Solscan Pro API v2.0 returns transactions in a list format
                tx_list = None
                if isinstance(data, list):
                    tx_list = data
                elif isinstance(data, dict):
                    tx_list = data.get("data", []) or data.get("result", []) or data.get("transactions", [])
                
                if not tx_list:
                    print(f"[SOLSCAN]   No transactions in response")
                    break
                
                print(f"[SOLSCAN]   Found {len(tx_list)} transactions in response")
                
                # Convert Solscan format to our RawTransaction format
                for tx_idx, tx in enumerate(tx_list):
                    if isinstance(tx, dict):
                        # Try to convert Solscan format directly
                        converted = self._convert_solscan_to_rpc_format(tx)
                        if converted:
                            transactions.append(RawTransaction(converted))
                        else:
                            # If conversion fails, fetch full details from RPC
                            signature = tx.get("txHash") or tx.get("signature") or tx.get("tx_hash") or tx.get("hash")
                            if signature:
                                print(f"[SOLSCAN]     Fetching full details for tx {tx_idx+1}: {signature[:8]}...")
                                full_tx = await self._get_transaction_details(signature)
                                if full_tx:
                                    transactions.append(RawTransaction(full_tx))
                
                # Update 'before' for next page (use signature of last transaction)
                if tx_list and len(tx_list) > 0:
                    last_tx = tx_list[-1]
                    before = last_tx.get("txHash") or last_tx.get("signature") or last_tx.get("tx_hash") or last_tx.get("hash")
                
                # Check if we got fewer transactions than requested (end of data)
                if len(tx_list) < request_limit:
                    print(f"[SOLSCAN]   No more transactions (got {len(tx_list)} < {request_limit})")
                    break
                
                await asyncio.sleep(0.5)  # Small delay between requests to avoid rate limiting
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    print(f"[SOLSCAN]   Authentication failed (401). Check your API key.")
                    print(f"[SOLSCAN]   Response: {e.response.text[:200]}")
                    break
                elif e.response.status_code == 429:
                    print(f"[SOLSCAN]   Rate limited (429), waiting 5 seconds...")
                    await asyncio.sleep(5)
                    continue
                else:
                    print(f"[SOLSCAN]   HTTP error {e.response.status_code}: {e.response.text[:200]}")
                    break
            except Exception as e:
                print(f"[SOLSCAN]   Error: {str(e)}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"[SOLSCAN] Successfully fetched {len(transactions)} transactions from Solscan")
        return transactions[:limit]
    
    async def _get_transaction_details(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get full transaction details for a signature."""
        # Try Solscan Pro API transaction detail endpoint first
        from app.config import settings
        
        if not settings.solscan_api_key:
            # Skip Solscan if no API key
            pass
        else:
            try:
                # Try v2.0 transaction endpoint
                url = f"{settings.solscan_api_url}/v2.0/transaction"
                params = {"tx": signature}
                headers = {"token": settings.solscan_api_key}
                
                response = await self.client.get(url, params=params, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    # Convert Solscan format to RPC-like format for compatibility
                    return self._convert_solscan_to_rpc_format(data)
            except:
                pass
        
        # Fallback to RPC
        try:
            result = await self._rpc_call("getTransaction", [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ])
            return result
        except:
            return None
    
    def _convert_solscan_to_rpc_format(self, solscan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Solscan transaction format to Solana RPC format."""
        # Extract transaction hash/signature
        signature = solscan_data.get("txHash") or solscan_data.get("signature") or solscan_data.get("tx_hash") or ""
        if not signature:
            return None
        
        # Extract block time (Solscan uses Unix timestamp)
        block_time = solscan_data.get("blockTime") or solscan_data.get("block_time")
        if not block_time and "time" in solscan_data:
            # Try to parse time string if provided
            try:
                from datetime import datetime
                time_str = solscan_data.get("time")
                if time_str:
                    # Parse various time formats
                    block_time = int(datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp())
            except:
                pass
        
        # Build RPC-like structure
        result = {
            "transaction": {
                "signatures": [signature],
                "message": {
                    "accountKeys": solscan_data.get("accountKeys", solscan_data.get("account_keys", [])),
                }
            },
            "meta": {
                "fee": solscan_data.get("fee", solscan_data.get("feeAmount", 0)),
                "preBalances": solscan_data.get("preBalances", solscan_data.get("pre_balances", [])),
                "postBalances": solscan_data.get("postBalances", solscan_data.get("post_balances", [])),
                "rewards": solscan_data.get("rewards", []),
                "preTokenBalances": solscan_data.get("preTokenBalances", solscan_data.get("pre_token_balances", [])),
                "postTokenBalances": solscan_data.get("postTokenBalances", solscan_data.get("post_token_balances", [])),
            },
            "blockTime": block_time,
        }
        
        # If we have minimal data, return None to trigger full fetch
        if not block_time and not result["meta"]["preBalances"]:
            return None
        
        return result
    
    async def _fetch_from_rpc(self, address: str, limit: int) -> List[RawTransaction]:
        """Fetch transactions using Solana RPC (fallback method)."""
        print(f"Fetching transactions from Solana RPC for {address}...")
        print(f"  RPC URL: {self.rpc_url}")
        
        # Get transaction signatures
        all_signatures = []
        before = None
        max_iterations = 10
        iteration = 0
        
        try:
            while iteration < max_iterations:
                params = {
                    "limit": min(limit - len(all_signatures), 1000)
                }
                if before:
                    params["before"] = before
                
                print(f"  Fetching signatures (iteration {iteration + 1}/{max_iterations})...")
                signatures_result = await self._rpc_call(
                    "getSignaturesForAddress",
                    [address, params]
                )
                
                if not signatures_result:
                    print(f"  No signatures returned")
                    break
                
                all_signatures.extend(signatures_result)
                print(f"  Got {len(signatures_result)} signatures (total: {len(all_signatures)})")
                
                if len(all_signatures) >= limit or len(signatures_result) < 1000:
                    break
                
                before = signatures_result[-1]["signature"]
                iteration += 1
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  Error fetching signatures from RPC: {e}")
            import traceback
            traceback.print_exc()
            raise WalletError(f"Failed to fetch transaction signatures: {str(e)}")
        
        if not all_signatures:
            print(f"  No transaction signatures found for address {address}")
            return []
        
        signatures = [sig["signature"] for sig in all_signatures]
        print(f"Found {len(signatures)} transaction signatures from RPC")
        
        # Fetch full transaction details
        transactions = []
        batch_size = 3
        
        print(f"Fetching {len(signatures)} transaction details in batches of {batch_size}...")
        
        for i in range(0, len(signatures), batch_size):
            batch = signatures[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(signatures) + batch_size - 1) // batch_size
            
            if i > 0:
                await asyncio.sleep(1.0)
            
            print(f"  Fetching batch {batch_num}/{total_batches} ({len(batch)} transactions)...")
            
            tasks = [
                self._rpc_call("getTransaction", [
                    sig,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                ])
                for sig in batch
            ]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful = 0
                for result in results:
                    if isinstance(result, Exception):
                        print(f"    Error in batch: {result}")
                        continue
                    if result:
                        transactions.append(RawTransaction(result))
                        successful += 1
                print(f"    Successfully fetched {successful}/{len(batch)} transactions in this batch")
            except Exception as e:
                print(f"    Error processing batch: {e}")
                continue
        
        print(f"Successfully fetched {len(transactions)} full transactions from RPC")
        return transactions[:limit]
    
    def parse_transaction(self, raw_tx: RawTransaction, wallet_address: Optional[str] = None) -> List[Transaction]:
        """
        Parse Solana transaction into normalized Transaction objects.
        
        Handles:
        - Transfers (SOL and SPL tokens)
        - Swaps (DEX transactions)
        - Staking rewards
        
        Args:
            raw_tx: Raw transaction data
            wallet_address: Optional wallet address for filtering rewards
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
        
        # Helper to get account pubkey (handles both string and dict formats)
        def get_account_pubkey(account, index):
            if isinstance(account, dict):
                return account.get("pubkey", "")
            elif isinstance(account, str):
                return account
            elif index < len(account_keys):
                acc = account_keys[index]
                if isinstance(acc, dict):
                    return acc.get("pubkey", "")
                return str(acc)
            return ""
        
        # Check for staking rewards first (from rewards array in meta)
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        reward_info = meta.get("rewards", [])
        
        # Debug: Always log reward info status
        print(f"[PARSE] Transaction {signature[:8]}... - rewards array length: {len(reward_info) if reward_info else 0}")
        if reward_info:
            print(f"  [DEBUG] Found {len(reward_info)} rewards in transaction {signature[:8]}...")
            for idx, r in enumerate(reward_info):
                print(f"    Reward {idx}: lamports={r.get('lamports', 0)}, pubkey={r.get('pubkey', '')[:8]}..., type={r.get('type', 'N/A')}")
        else:
            print(f"  [DEBUG] No rewards array found in meta, checking balance changes...")
            # Check if there are balance increases that might be rewards
            if pre_balances and post_balances:
                for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                    if post > pre:
                        diff = (post - pre) / 1e9
                        if diff > 0.001:  # Significant increase
                            print(f"    Balance increase detected: account {i}, +{diff} SOL (might be reward)")
        
        # Track which account indices have rewards to avoid double-counting
        reward_account_indices = set()
        
        # Detect staking rewards from the rewards array
        # In Solana, staking rewards appear in meta.rewards with positive lamports
        for reward in reward_info:
            reward_pubkey = reward.get("pubkey", "")
            reward_amount = reward.get("lamports", 0)
            reward_type = reward.get("type", "unknown")
            
            # Staking rewards have positive lamports
            # Note: The pubkey in rewards is the account that received the reward
            # For staking, this is typically a stake account, not the wallet directly
            if reward_amount > 0:
                reward_sol = Decimal(str(reward_amount)) / Decimal("1000000000")
                print(f"  [DEBUG] Processing reward: {reward_sol} SOL, pubkey={reward_pubkey[:8]}..., type={reward_type}")
                
                # Find the account index for this pubkey
                account_index = None
                for idx, account in enumerate(account_keys):
                    account_pubkey = get_account_pubkey(account, idx)
                    if account_pubkey == reward_pubkey:
                        account_index = idx
                        break
                
                # Add reward transaction
                # IMPORTANT: Staking rewards often go to stake accounts that may not be in account_keys
                # We should still create the reward transaction even if account_index is None
                if account_index is not None:
                    reward_account_indices.add(account_index)
                    reward_id = f"{signature}_reward_{account_index}_{len(transactions)}"
                else:
                    # Reward goes to a stake account not in account_keys - still create the transaction
                    reward_id = f"{signature}_reward_stake_{reward_pubkey[:8]}_{len(transactions)}"
                
                print(f"  [DEBUG] Creating staking reward transaction: {reward_sol} SOL, ID={reward_id}")
                transactions.append(Transaction(
                    id=reward_id,
                    timestamp=timestamp,
                    type=TransactionType.STAKE_REWARD,
                    chain="solana",
                    source="wallet",
                    token_out=SOL_TOKEN,
                    amount_out=reward_sol,
                    fee=Decimal("0"),
                    raw_data=tx_data,
                    audit_notes=f"Staking reward: {reward_sol} SOL from account {reward_pubkey[:8]}... (type: {reward_type})"
                ))
        
        # If no rewards found in rewards array, check for balance increases that might be staking rewards
        # This handles cases where rewards aren't in the rewards array
        if not reward_info or len([r for r in reward_info if r.get("lamports", 0) > 0]) == 0:
            print(f"  [DEBUG] No rewards in rewards array, checking balance changes for potential staking rewards...")
            if pre_balances and post_balances:
                # Check ALL accounts for balance increases that might be rewards
                # Staking rewards can go to stake accounts, not just the main wallet
                has_token_transfers = len(meta.get("preTokenBalances", [])) > 0 or len(meta.get("postTokenBalances", [])) > 0
                
                for idx in range(min(len(pre_balances), len(post_balances))):
                    # Skip if this account already has a reward
                    if idx in reward_account_indices:
                        continue
                    
                    pre_balance = pre_balances[idx]
                    post_balance = post_balances[idx]
                    balance_change = Decimal(str((post_balance - pre_balance) / 1e9))
                    
                    # If balance increased significantly and it's not the fee, it might be a reward
                    # Staking rewards are typically small but consistent increases
                    if balance_change > Decimal("0.0001") and abs(balance_change - fee) > Decimal("0.0001"):
                        # Check if this looks like a reward (not a transfer)
                        # Rewards are typically smaller and don't have corresponding token transfers
                        # Also check if this account is related to the wallet (either the wallet itself or a stake account)
                        account_pubkey = get_account_pubkey(account_keys[idx] if idx < len(account_keys) else None, idx)
                        is_wallet_account = wallet_address and account_pubkey == wallet_address
                        
                        # Consider it a reward if:
                        # 1. It's the wallet's account, OR
                        # 2. It's a small increase (< 10 SOL) with no token transfers (likely a stake account reward)
                        if is_wallet_account or (not has_token_transfers and balance_change < Decimal("10")):
                            print(f"  [DEBUG] Detected potential staking reward from balance change: account {idx} ({account_pubkey[:8] if account_pubkey else 'unknown'}...), +{balance_change} SOL")
                            transactions.append(Transaction(
                                id=f"{signature}_reward_balance_{idx}",
                                timestamp=timestamp,
                                type=TransactionType.STAKE_REWARD,
                                chain="solana",
                                source="wallet",
                                token_out=SOL_TOKEN,
                                amount_out=balance_change,
                                fee=Decimal("0"),
                                raw_data=tx_data,
                                audit_notes=f"Staking reward detected from balance change: {balance_change} SOL on account {idx} ({account_pubkey[:8] if account_pubkey else 'unknown'}...)"
                            ))
                            reward_account_indices.add(idx)  # Mark as processed
        
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
                
                # Try to get token symbol from known tokens or use mint address
                token_symbol = self._get_token_symbol(mint)
                
                token = Token(
                    symbol=token_symbol,
                    name=token_symbol,
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
        
        # Parse SOL transfers (excluding rewards which we already handled)
        sol_transfers = []
        if pre_balances and post_balances:
            for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                # Skip if this account already has a reward
                if i in reward_account_indices:
                    continue
                    
                diff = Decimal(str((post - pre) / 1e9))
                # Exclude fee and small changes
                # Note: fee is typically negative, so we check if the diff is significantly different from fee
                fee_abs = abs(fee)
                if abs(diff) > Decimal("0.000001") and abs(diff - fee) > Decimal("0.000001") and abs(diff + fee) > Decimal("0.000001"):
                    sol_transfers.append({
                        "index": i,
                        "diff": diff,
                        "is_in": diff > 0
                    })
        
        # Detect swaps: if we have both token transfers and SOL transfers, or multiple tokens
        # First, separate transactions by type (excluding rewards)
        transfer_transactions = [t for t in transactions if t.type == TransactionType.TRANSFER]
        all_token_ins = [t for t in transfer_transactions if t.token_in]
        all_token_outs = [t for t in transfer_transactions if t.token_out]
        sol_ins = [t for t in sol_transfers if t["is_in"]]
        sol_outs = [t for t in sol_transfers if not t["is_in"]]
        
        # Check if this looks like a swap
        is_swap = False
        swap_token_in = None
        swap_token_out = None
        swap_amount_in = None
        swap_amount_out = None
        transactions_to_remove = []
        
        # Case 1: Token to Token swap (token in + token out, no SOL changes)
        if len(all_token_ins) == 1 and len(all_token_outs) == 1 and len(sol_transfers) == 0:
            is_swap = True
            swap_token_in = all_token_ins[0].token_in
            swap_token_out = all_token_outs[0].token_out
            swap_amount_in = all_token_ins[0].amount_in
            swap_amount_out = all_token_outs[0].amount_out
            transactions_to_remove = all_token_ins + all_token_outs
        
        # Case 2: SOL to Token swap
        # When swapping SOL for a token: you send SOL (out) and receive token (in)
        elif len(sol_outs) == 1 and len(all_token_outs) == 1 and len(all_token_ins) == 0:
            is_swap = True
            swap_token_in = SOL_TOKEN  # You send SOL
            swap_token_out = all_token_outs[0].token_out  # You receive token
            swap_amount_in = Decimal(str(abs(sol_outs[0]["diff"])))  # Amount of SOL sent
            swap_amount_out = all_token_outs[0].amount_out  # Amount of token received
            transactions_to_remove = all_token_outs
        
        # Case 3: Token to SOL swap
        # When swapping token for SOL: you send token (out) and receive SOL (in)
        elif len(all_token_ins) == 1 and len(sol_ins) == 1 and len(all_token_outs) == 0:
            is_swap = True
            swap_token_in = all_token_ins[0].token_in  # You send token
            swap_token_out = SOL_TOKEN  # You receive SOL
            swap_amount_in = all_token_ins[0].amount_in  # Amount of token sent
            swap_amount_out = Decimal(str(sol_ins[0]["diff"]))  # Amount of SOL received
            transactions_to_remove = all_token_ins
        
        # Create swap transaction if detected and remove individual transfers
        if is_swap:
            # Remove the individual transfer transactions
            transactions = [t for t in transactions if t not in transactions_to_remove]
            # Add the swap transaction
            transactions.append(Transaction(
                id=f"{signature}_swap",
                timestamp=timestamp,
                type=TransactionType.SWAP,
                chain="solana",
                source="wallet",
                token_in=swap_token_in,
                token_out=swap_token_out,
                amount_in=swap_amount_in,
                amount_out=swap_amount_out,
                fee=fee,
                raw_data=tx_data,
                audit_notes=f"Swap: {swap_amount_in} {swap_token_in.symbol if swap_token_in else '?'} -> {swap_amount_out} {swap_token_out.symbol if swap_token_out else '?'}"
            ))
        else:
            # Add SOL transfers as regular transfers (if not part of a swap)
            for sol_tx in sol_transfers:
                if sol_tx["is_in"]:
                    transactions.append(Transaction(
                        id=f"{signature}_sol_in_{sol_tx['index']}",
                        timestamp=timestamp,
                        type=TransactionType.TRANSFER,
                        chain="solana",
                        source="wallet",
                        token_out=SOL_TOKEN,
                        amount_out=Decimal(str(sol_tx["diff"])),
                        fee=Decimal("0"),
                        raw_data=tx_data,
                        audit_notes=f"SOL transfer received"
                    ))
                else:
                    transactions.append(Transaction(
                        id=f"{signature}_sol_out_{sol_tx['index']}",
                        timestamp=timestamp,
                        type=TransactionType.TRANSFER,
                        chain="solana",
                        source="wallet",
                        token_in=SOL_TOKEN,
                        amount_in=Decimal(str(abs(sol_tx["diff"]))),
                        fee=Decimal("0"),
                        raw_data=tx_data,
                        audit_notes=f"SOL transfer sent"
                    ))
        
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
