import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ScenarioSimulatorCard } from '../App.jsx'

describe('ScenarioSimulatorCard Component', () => {
  const sampleModelInfo = {
    target: 'sales',
    features: [
      { name: 'discount', type: 'number', default: 0.1 },
      { name: 'region', type: 'category', options: ['Dhaka', 'Sylhet'], default: 'Dhaka' },
    ],
  }

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders driver controls and input fields', () => {
    render(<ScenarioSimulatorCard sessionId="sess-1" modelInfo={sampleModelInfo} category="general" />)

    expect(screen.getByText('Scenario Simulator')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Try: increase discount by 10%/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Parse/i })).toBeInTheDocument()
  })

  it('parses natural language prompt and prefills driver changes', async () => {
    const mockParseResponse = {
      parsed: true,
      feature: 'discount',
      mode: 'percent',
      value: 10,
      interpretation: 'percent discount by 10',
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockParseResponse,
    })

    render(<ScenarioSimulatorCard sessionId="sess-1" modelInfo={sampleModelInfo} category="general" />)

    const input = screen.getByPlaceholderText(/Try: increase discount by 10%/i)
    fireEvent.change(input, { target: { value: 'increase discount by 10%' } })

    const parseBtn = screen.getByRole('button', { name: /Parse/i })
    fireEvent.click(parseBtn)

    await waitFor(() => {
      expect(screen.getByText('percent discount by 10')).toBeInTheDocument()
    })
  })

  it('runs scenario simulation and displays baseline vs scenario impact', async () => {
    const mockSimulateResponse = {
      target: 'sales',
      baseline_prediction: { prediction: 500 },
      scenario_prediction: { prediction: 550 },
      impact: {
        type: 'regression',
        delta: 50,
        pct_change: 10.0,
        direction: 'increase',
      },
      validation: {
        reasons: ['Baseline calculation', 'What-if simulation estimate using Random Forest'],
      },
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSimulateResponse,
    })

    render(<ScenarioSimulatorCard sessionId="sess-1" modelInfo={sampleModelInfo} category="general" />)

    const runBtn = screen.getByRole('button', { name: /Run scenario/i })
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(screen.getByText('increase 50')).toBeInTheDocument()
      expect(screen.getByText('500')).toBeInTheDocument()
      expect(screen.getByText('550')).toBeInTheDocument()
    })
  })
})
