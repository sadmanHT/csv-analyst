import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PredictInputCard } from '../App.jsx'

describe('PredictInputCard Component', () => {
  const sampleModelInfo = {
    target: 'revenue',
    features: [
      { name: 'quantity', type: 'number', default: 5 },
      { name: 'category', type: 'category', options: ['Electronics', 'Home'], default: 'Electronics' },
    ],
  }

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders input controls and default feature values', () => {
    render(<PredictInputCard sessionId="sess-1" modelInfo={sampleModelInfo} />)

    expect(screen.getByText('Predict a New Case')).toBeInTheDocument()
    expect(screen.getByDisplayValue('5')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Electronics')).toBeInTheDocument()
  })

  it('submits form values and displays prediction output', async () => {
    const mockResponse = {
      target: 'revenue',
      prediction: 145.5,
      prediction_interval: {
        lower: 120.0,
        upper: 170.0,
        confidence: 0.9,
      },
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    })

    render(<PredictInputCard sessionId="sess-1" modelInfo={sampleModelInfo} />)

    const btn = screen.getByRole('button', { name: /Predict revenue/i })
    fireEvent.click(btn)

    await waitFor(() => {
      expect(screen.getByText('Predicted revenue')).toBeInTheDocument()
      expect(screen.getByText('145.5')).toBeInTheDocument()
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/predict_input'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          session_id: 'sess-1',
          values: { quantity: 5, category: 'Electronics' },
        }),
      })
    )
  })
})
