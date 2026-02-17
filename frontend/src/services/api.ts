/** API client for backend communication */
import axios from 'axios'
import type {
  WalletRequest,
  WalletResponse,
  TaxCalculationRequest,
  TaxReport,
  Country,
} from './types'

// Use proxy in development, direct URL in production
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? '/api/v1' : 'http://localhost:8000/api/v1')

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes timeout for tax calculations
})

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data)
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response from ${response.config.url}:`, response.status)
    return response
  },
  (error) => {
    console.error('[API] Response error:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
    })
    return Promise.reject(error)
  }
)

export const walletApi = {
  process: async (request: WalletRequest): Promise<WalletResponse> => {
    const response = await api.post<WalletResponse>('/wallets/process', request)
    return response.data
  },
  
  validate: async (address: string): Promise<{ address: string; valid: boolean; message?: string }> => {
    const response = await api.get(`/wallets/validate/${address}`)
    return response.data
  },
}

export const taxApi = {
  calculate: async (request: TaxCalculationRequest, format: string = 'json'): Promise<TaxReport | Blob> => {
    if (format === 'excel') {
      const response = await api.post('/tax/calculate', request, {
        params: { format: 'excel' },
        responseType: 'blob'
      })
      return response.data
    } else {
      const response = await api.post<TaxReport>('/tax/calculate', request, {
        params: { format: 'json' }
      })
      return response.data
    }
  },
  
  listCountries: async (): Promise<{ countries: Country[] }> => {
    const response = await api.get('/tax/countries')
    return response.data
  },
}

export const cexApi = {
  connect: async (exchange: string, apiKey: string, apiSecret?: string, passphrase?: string) => {
    const response = await api.post('/cex/connect', {
      exchange,
      api_key: apiKey,
      api_secret: apiSecret,
      passphrase,
    })
    return response.data
  },
  
  uploadCsv: async (exchange: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post(`/cex/upload/${exchange}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

export const reportsApi = {
  generate: async (country: string, year: number, format: string = 'excel') => {
    const response = await api.post('/reports/generate', {
      country,
      year,
      format,
    }, {
      responseType: 'blob',
    })
    return response.data
  },
}

export default api
