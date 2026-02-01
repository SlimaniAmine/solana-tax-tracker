import { useState } from 'react'
import type { TaxReport } from '../services/types'
import { reportsApi } from '../services/api'
import * as XLSX from 'xlsx'

interface ResultsDisplayProps {
  report: TaxReport
}

function ResultsDisplay({ report }: ResultsDisplayProps) {
  const [exporting, setExporting] = useState(false)

  const handleExportExcel = async () => {
    setExporting(true)
    try {
      // Generate Excel on frontend using SheetJS
      const ws = XLSX.utils.json_to_sheet([
        {
          'Country': report.country,
          'Year': report.year,
          'Total Gains (EUR)': report.summary.total_gains_eur,
          'Total Losses (EUR)': report.summary.total_losses_eur,
          'Net Gain/Loss (EUR)': report.summary.net_gain_loss_eur,
          'Staking Rewards (EUR)': report.summary.staking_rewards_eur,
          'Taxable Amount (EUR)': report.summary.taxable_amount_eur,
          'Transaction Count': report.summary.transaction_count,
        }
      ])
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Summary')
      
      if (report.transactions.length > 0) {
        const txData = report.transactions.map(tx => ({
          'ID': tx.id,
          'Timestamp': tx.timestamp,
          'Type': tx.type,
          'Chain': tx.chain,
          'Source': tx.source,
          'Token In': tx.token_in?.symbol || '',
          'Amount In': tx.amount_in || '',
          'Token Out': tx.token_out?.symbol || '',
          'Amount Out': tx.amount_out || '',
          'Price In (USD)': tx.price_in_usd || '',
          'Price Out (USD)': tx.price_out_usd || '',
          'Price In (EUR)': tx.price_in_eur || '',
          'Price Out (EUR)': tx.price_out_eur || '',
          'Cost Basis (EUR)': tx.cost_basis_eur || '',
          'Proceeds (EUR)': tx.proceeds_eur || '',
          'Gain/Loss (EUR)': tx.gain_loss_eur || '',
          'Holding Period (Days)': tx.holding_period_days || '',
          'Fee (EUR)': tx.fee_eur || '',
          'Audit Notes': tx.audit_notes || '',
        }))
        const txWs = XLSX.utils.json_to_sheet(txData)
        XLSX.utils.book_append_sheet(wb, txWs, 'Transactions')
      }
      
      XLSX.writeFile(wb, `tax-report-${report.country}-${report.year}.xlsx`)
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
