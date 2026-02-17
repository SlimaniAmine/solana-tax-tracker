import { useState } from 'react'
import type { TaxReport, TaxCalculationRequest } from '../services/types'
import { taxApi } from '../services/api'

interface ResultsDisplayProps {
  report: TaxReport
  calculationRequest?: TaxCalculationRequest
}

function ResultsDisplay({ report, calculationRequest }: ResultsDisplayProps) {
  const [exporting, setExporting] = useState(false)

  const handleExportExcel = async () => {
    setExporting(true)
    try {
      // Use backend API to generate Excel file
      // Use stored calculation request if available, otherwise use report data
      const request: TaxCalculationRequest = calculationRequest || {
        country: report.country,
        year: report.year,
        wallet_addresses: [],
        include_cex: false,
      }
      
      const response = await taxApi.calculate(request, 'excel') as Blob
      
      // Download the Excel file
      const url = window.URL.createObjectURL(response)
      const a = document.createElement('a')
      a.href = url
      a.download = `tax-report-${report.country}-${report.year}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error exporting Excel:', err)
      alert('Error exporting Excel file. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-gray-900">
          Tax Summary
        </h3>
        <button
          onClick={handleExportExcel}
          disabled={exporting}
          className="bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:bg-gray-400"
        >
          {exporting ? 'Exporting...' : 'Export to Excel'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Gains</div>
          <div className="text-2xl font-bold text-green-600">
            {parseFloat(report.summary.total_gains_eur).toFixed(2)} EUR
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Losses</div>
          <div className="text-2xl font-bold text-red-600">
            {parseFloat(report.summary.total_losses_eur).toFixed(2)} EUR
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Net Gain/Loss</div>
          <div className={`text-2xl font-bold ${
            parseFloat(report.summary.net_gain_loss_eur) >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {parseFloat(report.summary.net_gain_loss_eur).toFixed(2)} EUR
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Staking Rewards</div>
          <div className="text-2xl font-bold text-blue-600">
            {parseFloat(report.summary.staking_rewards_eur).toFixed(2)} EUR
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Taxable Amount</div>
          <div className="text-2xl font-bold text-purple-600">
            {parseFloat(report.summary.taxable_amount_eur).toFixed(2)} EUR
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">Transactions</div>
          <div className="text-2xl font-bold text-gray-900">
            {report.summary.transaction_count}
          </div>
        </div>
      </div>

      {report.transactions.length > 0 && (
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4">
            Transaction Details
          </h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Token In</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Token Out</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Gain/Loss (EUR)</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {report.transactions.slice(0, 100).map((tx) => (
                  <tr key={tx.id}>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {new Date(tx.timestamp).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{tx.type}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {tx.token_in?.symbol || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {tx.token_out?.symbol || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {tx.gain_loss_eur ? parseFloat(tx.gain_loss_eur).toFixed(2) : '-'} EUR
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {report.transactions.length > 100 && (
              <p className="mt-4 text-sm text-gray-600">
                Showing first 100 transactions. Full list available in Excel export.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ResultsDisplay
