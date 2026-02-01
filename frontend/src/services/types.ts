/** TypeScript types for API responses */

export interface Transaction {
  id: string
  timestamp: string
  type: 'BUY' | 'SELL' | 'SWAP' | 'TRANSFER' | 'STAKE_REWARD' | 'DEPOSIT' | 'WITHDRAWAL'
  chain: string
  source: string
  token_in?: Token
  token_out?: Token
  amount_in?: string
  amount_out?: string
  price_in_usd?: string
  price_out_usd?: string
  price_in_eur?: string
  price_out_eur?: string
  cost_basis_eur?: string
  proceeds_eur?: string
  gain_loss_eur?: string
  holding_period_days?: number
  fee?: string
  fee_token?: Token
  fee_eur?: string
}

export interface Token {
  symbol: string
  name: string
  address: string
  decimals: number
  chain: string
}

export interface TaxSummary {
  total_gains_eur: string
  total_losses_eur: string
  net_gain_loss_eur: string
  staking_rewards_eur: string
  taxable_amount_eur: string
  transaction_count: number
}

export interface TaxReport {
  country: string
  year: number
  generated_at: string
  summary: TaxSummary
  transactions: Transaction[]
  audit_trail?: string
}

export interface WalletRequest {
  addresses: string[]
  year?: number
}

export interface WalletResponse {
  addresses: string[]
  transaction_count: number
  status: string
  message?: string
}

export interface TaxCalculationRequest {
  country: string
  year: number
  wallet_addresses?: string[]
  include_cex?: boolean
}

export interface Country {
  code: string
  name: string
  supported: boolean
}
