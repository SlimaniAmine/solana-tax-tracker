import { useMutation } from '@tanstack/react-query'
import { taxApi } from '../services/api'
import type { TaxCalculationRequest, TaxReport } from '../services/types'

export function useTaxCalculation() {
  return useMutation<TaxReport, Error, TaxCalculationRequest>({
    mutationFn: (request) => taxApi.calculate(request),
  })
}
