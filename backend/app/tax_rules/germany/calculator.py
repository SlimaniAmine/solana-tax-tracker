"""German tax calculation engine."""
from typing import List, Dict
from decimal import Decimal
from datetime import datetime, timedelta
from collections import deque
from app.models.transaction import Transaction, TransactionType
from app.models.report import TaxReport, TaxSummary
from app.tax_rules.base import TaxRuleEngine, CostBasisMethod, HoldingPeriodRule
from app.tax_rules.germany.rules import (
    get_germany_holding_period_rule,
    GERMANY_COST_BASIS_METHOD,
    GERMANY_STAKING_AS_INCOME,
    GERMANY_TAX_FREE_THRESHOLD_EUR
)


class GermanyTaxCalculator(TaxRuleEngine):
    """Tax calculator for Germany."""
    
    def __init__(self):
        self.holding_period_rule = get_germany_holding_period_rule()
        self.cost_basis_method = GERMANY_COST_BASIS_METHOD
    
    def calculate_tax(self, transactions: List[Transaction], year: int) -> TaxReport:
        """
        Calculate taxes according to German tax rules.
        
        German tax rules:
        - 1-year holding period for tax-free capital gains
        - FIFO cost basis method
        - Staking rewards treated as income
        - 600 EUR tax-free threshold per year
        """
        # Filter transactions by year
        year_transactions = [tx for tx in transactions if tx.timestamp.year == year]
        
        # Separate staking rewards from other transactions
        staking_rewards = [
            tx for tx in year_transactions
            if tx.type == TransactionType.STAKE_REWARD
        ]
        
        print(f"[TAX CALC] Found {len(staking_rewards)} staking rewards for year {year}")
        for idx, tx in enumerate(staking_rewards):
            print(f"  Reward {idx+1}: {tx.amount_out} SOL, price_out_eur={tx.price_out_eur}, timestamp={tx.timestamp}")
        
        # Calculate staking rewards total (treated as income)
        staking_rewards_eur = Decimal("0")
        for tx in staking_rewards:
            if tx.amount_out and tx.price_out_eur:
                reward_value = tx.price_out_eur * tx.amount_out
                staking_rewards_eur += reward_value
                print(f"  Adding reward value: {tx.amount_out} SOL * {tx.price_out_eur} EUR = {reward_value} EUR")
            else:
                print(f"  WARNING: Reward missing price or amount: amount_out={tx.amount_out}, price_out_eur={tx.price_out_eur}")
        
        print(f"[TAX CALC] Total staking rewards EUR: {staking_rewards_eur}")
        
        # Process capital gains/losses (BUY, SELL, SWAP)
        capital_gains_transactions = [
            tx for tx in year_transactions
            if tx.type in [TransactionType.BUY, TransactionType.SELL, TransactionType.SWAP]
        ]
        
        # Track holdings using FIFO
        holdings: Dict[str, deque] = {}  # token -> deque of (amount, cost_basis_eur, timestamp)
        total_gains = Decimal("0")
        total_losses = Decimal("0")
        
        for tx in sorted(capital_gains_transactions, key=lambda x: x.timestamp):
            if tx.type == TransactionType.BUY or (tx.type == TransactionType.SWAP and tx.token_in):
                # Add to holdings
                if tx.token_in:
                    token_key = tx.token_in.address
                    if token_key not in holdings:
                        holdings[token_key] = deque()
                    
                    cost_basis_eur = (tx.price_in_eur * tx.amount_in) if tx.price_in_eur and tx.amount_in else Decimal("0")
                    holdings[token_key].append((
                        tx.amount_in,
                        cost_basis_eur,
                        tx.timestamp
                    ))
                    
                    tx.cost_basis_eur = cost_basis_eur
                    tx.audit_notes = f"Purchase: {tx.amount_in} {tx.token_in.symbol} at {tx.price_in_eur} EUR"
            
            elif tx.type == TransactionType.SELL or (tx.type == TransactionType.SWAP and tx.token_out):
                # Remove from holdings using FIFO
                if tx.token_out:
                    token_key = tx.token_out.address
                    if token_key in holdings and holdings[token_key]:
                        amount_to_sell = tx.amount_out
                        proceeds_eur = (tx.price_out_eur * tx.amount_out) if tx.price_out_eur and tx.amount_out else Decimal("0")
                        cost_basis_eur = Decimal("0")
                        
                        # FIFO: sell oldest holdings first
                        while amount_to_sell > 0 and holdings[token_key]:
                            holding_amount, holding_cost, holding_timestamp = holdings[token_key][0]
                            
                            if holding_amount <= amount_to_sell:
                                # Sell entire holding
                                cost_basis_eur += holding_cost
                                amount_to_sell -= holding_amount
                                holdings[token_key].popleft()
                            else:
                                # Sell partial holding
                                ratio = amount_to_sell / holding_amount
                                cost_basis_eur += holding_cost * ratio
                                holdings[token_key][0] = (
                                    holding_amount - amount_to_sell,
                                    holding_cost * (1 - ratio),
                                    holding_timestamp
                                )
                                amount_to_sell = Decimal("0")
                        
                        # Calculate gain/loss
                        gain_loss = proceeds_eur - cost_basis_eur
                        
                        # Check holding period
                        if holdings[token_key]:
                            # Use the oldest remaining holding to check period
                            oldest_holding = holdings[token_key][0]
                            holding_period = (tx.timestamp - oldest_holding[2]).days
                        else:
                            # All holdings sold, use average
                            holding_period = 0  # Simplified - should track per holding
                        
                        tx.cost_basis_eur = cost_basis_eur
                        tx.proceeds_eur = proceeds_eur
                        tx.gain_loss_eur = gain_loss
                        tx.holding_period_days = holding_period
                        
                        # Apply holding period rule
                        if holding_period >= self.holding_period_rule.days:
                            # Long-term: tax-free (if under threshold)
                            tx.audit_notes = f"Long-term gain/loss (holding period: {holding_period} days)"
                        else:
                            # Short-term: taxable
                            tx.audit_notes = f"Short-term gain/loss (holding period: {holding_period} days)"
                        
                        if gain_loss > 0:
                            total_gains += gain_loss
                        else:
                            total_losses += abs(gain_loss)
        
        # Calculate net gain/loss
        net_gain_loss = total_gains - total_losses
        
        # Calculate taxable amount
        # In Germany: gains are tax-free if under 600 EUR threshold
        taxable_amount = max(Decimal("0"), net_gain_loss + staking_rewards_eur - GERMANY_TAX_FREE_THRESHOLD_EUR)
        
        # Create summary
        summary = TaxSummary(
            total_gains_eur=total_gains,
            total_losses_eur=total_losses,
            net_gain_loss_eur=net_gain_loss,
            staking_rewards_eur=staking_rewards_eur,
            taxable_amount_eur=taxable_amount,
            transaction_count=len(year_transactions)
        )
        
        # Create audit trail
        audit_trail = f"""
German Tax Calculation for {year}
================================
Holding Period Rule: {self.holding_period_rule.days} days
Cost Basis Method: {self.cost_basis_method.value}
Staking Rewards: Treated as income
Tax-Free Threshold: {GERMANY_TAX_FREE_THRESHOLD_EUR} EUR

Summary:
- Total Gains: {total_gains} EUR
- Total Losses: {total_losses} EUR
- Net Gain/Loss: {net_gain_loss} EUR
- Staking Rewards: {staking_rewards_eur} EUR
- Taxable Amount: {taxable_amount} EUR
- Transactions Processed: {len(year_transactions)}
        """.strip()
        
        return TaxReport(
            country="DE",
            year=year,
            generated_at=datetime.utcnow(),
            summary=summary,
            transactions=year_transactions,
            audit_trail=audit_trail
        )
    
    def get_holding_period_rule(self) -> HoldingPeriodRule:
        """Get German holding period rule (1 year)."""
        return self.holding_period_rule
    
    def get_cost_basis_method(self) -> CostBasisMethod:
        """Get German cost basis method (FIFO)."""
        return self.cost_basis_method
    
    def get_country_code(self) -> str:
        """Get country code."""
        return "DE"
