import { useState } from 'react'

interface WalletInputProps {
  wallets: string[]
  onChange: (wallets: string[]) => void
}

function WalletInput({ wallets, onChange }: WalletInputProps) {
  const maxWallets = 10

  const addWallet = () => {
    if (wallets.length < maxWallets) {
      onChange([...wallets, ''])
    }
  }

  const removeWallet = (index: number) => {
    if (wallets.length > 1) {
      onChange(wallets.filter((_, i) => i !== index))
    }
  }

  const updateWallet = (index: number, value: string) => {
    const newWallets = [...wallets]
    newWallets[index] = value
    onChange(newWallets)
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Solana Wallet Addresses (up to {maxWallets})
      </label>
      {wallets.map((wallet, index) => (
        <div key={index} className="flex gap-2">
          <input
            type="text"
            value={wallet}
            onChange={(e) => updateWallet(index, e.target.value)}
            placeholder="Enter Solana wallet address"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {wallets.length > 1 && (
            <button
              onClick={() => removeWallet(index)}
              className="px-4 py-2 text-red-600 hover:text-red-700 border border-red-300 rounded-lg hover:bg-red-50"
            >
              Remove
            </button>
          )}
        </div>
      ))}
      {wallets.length < maxWallets && (
        <button
          onClick={addWallet}
          className="text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          + Add Wallet
        </button>
      )}
    </div>
  )
}

export default WalletInput
