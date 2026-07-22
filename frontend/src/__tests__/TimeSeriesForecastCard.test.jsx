import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TimeSeriesForecastCard } from '../App.jsx'

describe('TimeSeriesForecastCard Component', () => {
  const sampleUpload = {
    session_id: 'sess-ts',
    columns: ['date', 'revenue', 'category'],
    numeric_stats: {
      revenue: { mean: 500, min: 100, max: 900 },
    },
  }

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders time-series controls and target metric selector', () => {
    render(<TimeSeriesForecastCard sessionId="sess-ts" upload={sampleUpload} />)

    expect(screen.getByText('Time-Series Forecast')).toBeInTheDocument()
    expect(screen.getByDisplayValue('date')).toBeInTheDocument()
    expect(screen.getByDisplayValue('revenue')).toBeInTheDocument()
  })

  it('submits forecast request and renders trend direction metric', async () => {
    const mockForecastResponse = {
      date_column: 'date',
      target_column: 'revenue',
      periods: 12,
      metrics: {
        trend_direction: 'upward',
        growth_rate_pct: 18.5,
      },
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockForecastResponse,
    })

    render(<TimeSeriesForecastCard sessionId="sess-ts" upload={sampleUpload} />)

    const btn = screen.getByRole('button', { name: /Forecast revenue/i })
    fireEvent.click(btn)

    await waitFor(() => {
      expect(screen.getByText(/upward \(18.5%\)/i)).toBeInTheDocument()
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/forecast'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          session_id: 'sess-ts',
          date_column: 'date',
          target_column: 'revenue',
          periods: 12,
        }),
      })
    )
  })
})
