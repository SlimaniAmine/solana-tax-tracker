import { useState } from 'react'
import { cexApi } from '../services/api'

function CexIntegration() {
  const [expanded, setExpanded] = useState(false)
  const [selectedExchange, setSelectedExchange] = useState<string>('')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const exchanges = [
    { value: 'kraken', label: 'Kraken' },
    { value: 'coinbase', label: 'Coinbase' },
  ]

  const handleApiConnect = async () => {
    if (!selectedExchange || !apiKey) {
      setError('Please select an exchange and enter API key')
      return
    }

    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      await cexApi.connect(selectedExchange, apiKey, apiSecret, passphrase)
      setSuccess(`Successfully connected to ${selectedExchange}`)
      // Reset form
      setApiKey('')
      setApiSecret('')
      setPassphrase('')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to connect')
    } finally {
      setLoading(false)
    }
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedExchange) {
      setError('Please select an exchange and choose a file')
      return
    }

    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      await cexApi.uploadCsv(selectedExchange, file)
      setSuccess(`Successfully uploaded ${file.name}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload CSV')
    } finally {
      setLoading(false)
      e.target.value = '' // Reset file input
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left font-medium text-gray-700"
      >
        <span>Centralized Exchange (CEX) Integration</span>
        <span className="text-gray-400">{expanded ? '−' : '+'}</span>
      </button>

      {expanded && (
        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Exchange
            </label>
            <select
              value={selectedExchange}
              onChange={(e) => setSelectedExchange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2"
            >
              <option value="">Choose an exchange...</option>
              {exchanges.map((ex) => (
                <option key={ex.value} value={ex.value}>
                  {ex.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter API key"
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Secret (optional)
              </label>
              <input
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Enter API secret"
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
              />
            </div>

            {selectedExchange === 'coinbase' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Passphrase (Coinbase)
                </label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="Enter passphrase"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2"
                />
              </div>
            )}

            <button
              onClick={handleApiConnect}
              disabled={loading || !selectedExchange || !apiKey}
              className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:bg-gray-400"
            >
              {loading ? 'Connecting...' : 'Connect via API'}
            </button>
          </div>

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Or Upload CSV File
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              disabled={!selectedExchange || loading}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 disabled:bg-gray-100"
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
          {success && (
            <div className="text-green-600 text-sm">{success}</div>
          )}
        </div>
      )}
    </div>
  )
}

export default CexIntegration
