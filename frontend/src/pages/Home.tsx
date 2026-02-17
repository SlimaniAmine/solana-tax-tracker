import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import WalletInput from '../components/WalletInput'
import CexIntegration from '../components/CexIntegration'
import CountrySelector from '../components/CountrySelector'
import YearSelector from '../components/YearSelector'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { taxApi } from '../services/api'

function Home() {
  const [wallets, setWallets] = useState<string[]>([''])
  const [country, setCountry] = useState<string>('DE')
  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleProcess = async () => {
    setError(null)
    setLoading(true)
    
    try {
      const validWallets = wallets.filter(w => w.trim() !== '')
      if (validWallets.length === 0) {
        setError('Please enter at least one wallet address')
        setLoading(false)
        return
      }

      const result = await taxApi.calculate({
        country,
        year,
        wallet_addresses: validWallets,
        include_cex: true,
      }, 'json')

      // Navigate to results page with data and original request
      navigate('/results', { 
        state: { 
          report: result,
          calculationRequest: {
            country,
            year,
            wallet_addresses: validWallets,
            include_cex: true,
          }
        } 
      })
    } catch (err: any) {
      console.error('Tax calculation error:', err)
      let errorMessage = 'Failed to process tax calculation'
      
      if (err.code === 'ECONNREFUSED' || err.message?.includes('Network Error')) {
        errorMessage = 'Cannot connect to backend server. Please make sure the backend is running on http://localhost:8000'
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Crypto Tax Calculator
        </h2>
        <p className="text-gray-600">
          Enter your Solana wallet addresses and calculate your tax obligations
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <WalletInput
          wallets={wallets}
          onChange={setWallets}
        />

        <CexIntegration />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CountrySelector
            value={country}
            onChange={setCountry}
          />
          <YearSelector
            value={year}
            onChange={setYear}
          />
        </div>

        {error && <ErrorMessage message={error} />}

        <button
          onClick={handleProcess}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
        >
          {loading ? (
            <>
              <LoadingSpinner className="mr-2" />
              Processing...
            </>
          ) : (
            'Calculate Tax'
          )}
        </button>
      </div>
    </div>
  )
}

export default Home
