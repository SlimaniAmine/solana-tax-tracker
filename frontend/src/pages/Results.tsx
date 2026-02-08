import { useLocation, useNavigate } from 'react-router-dom'
import ResultsDisplay from '../components/ResultsDisplay'
import type { TaxReport, TaxCalculationRequest } from '../services/types'

function Results() {
  const location = useLocation()
  const navigate = useNavigate()
  const report = location.state?.report as TaxReport | undefined
  const calculationRequest = location.state?.calculationRequest as TaxCalculationRequest | undefined

  if (!report) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600">No results available. Please calculate taxes first.</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700"
        >
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold text-gray-900">
          Tax Report {report.year}
        </h2>
        <button
          onClick={() => navigate('/')}
          className="text-blue-600 hover:text-blue-700"
        >
          ← Back
        </button>
      </div>
      <ResultsDisplay report={report} calculationRequest={calculationRequest} />
    </div>
  )
}

export default Results
