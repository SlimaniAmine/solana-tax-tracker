import { useState, useEffect } from 'react'
import { taxApi } from '../services/api'

interface CountrySelectorProps {
  value: string
  onChange: (value: string) => void
}

function CountrySelector({ value, onChange }: CountrySelectorProps) {
  const [countries, setCountries] = useState<Array<{ code: string; name: string; supported: boolean }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    taxApi.listCountries()
      .then((data) => setCountries(data.countries))
      .catch(() => {
        // Fallback if API fails
        setCountries([{ code: 'DE', name: 'Germany', supported: true }])
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Country
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {loading ? (
          <option>Loading...</option>
        ) : (
          countries.map((country) => (
            <option key={country.code} value={country.code}>
              {country.name} {country.supported ? '' : '(Coming Soon)'}
            </option>
          ))
        )}
      </select>
    </div>
  )
}

export default CountrySelector
