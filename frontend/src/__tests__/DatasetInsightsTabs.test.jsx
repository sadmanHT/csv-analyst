import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { InsightsPanelErrorBoundary, formatNumber, ExportCard, TimeSeriesForecastCard, DatasetInsightsPanel } from '../App.jsx'

describe('Dataset Insights Tabs and Error Boundary', () => {
  const sampleUpload = {
    session_id: 'sess-tab-test',
    filename: 'diabetes.csv',
    rows: 768,
    columns: ['Pregnancies', 'Glucose', 'BloodPressure', 'Outcome'],
    missing_pct: 0,
    duplicate_rows: 0,
    numeric_stats: {
      Glucose: { mean: 120.8, min: 0, max: 199, std: 31.9 },
      BloodPressure: { mean: 69.1, min: 0, max: 122, std: 19.3 },
    },
    quality_report: { issues: [] },
    decision_brief: { readiness_score: 85, summary: 'Sample dataset overview' },
  }

  it('renders InsightsPanelErrorBoundary fallback when child component throws', () => {
    const ProblemChild = () => {
      throw new Error('Test rendering crash in right panel')
    }

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <InsightsPanelErrorBoundary>
        <ProblemChild />
      </InsightsPanelErrorBoundary>
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Dataset Insights could not be displayed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('formats numbers safely without throwing on invalid inputs', () => {
    expect(formatNumber(12.345, 1)).toBe('12.3')
    expect(formatNumber(null)).toBe('Not available')
    expect(formatNumber(undefined)).toBe('Not available')
    expect(formatNumber('invalid')).toBe('Not available')
  })

  it('renders ExportCard safely with undefined messages or no export data', () => {
    render(<ExportCard upload={sampleUpload} messages={undefined} category="general" />)
    expect(screen.getByText(/Export Report/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /PDF/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /PPTX/i })).toBeDisabled()
  })

  it('renders ExportCard with empty arrays and undefined dashboardBlueprint', () => {
    render(
      <ExportCard
        upload={sampleUpload}
        messages={[]}
        items={[]}
        formats={[]}
        files={[]}
        dashboardBlueprint={undefined}
      />
    )
    expect(screen.getByText(/Export Report/i)).toBeInTheDocument()
    expect(screen.getByText(/Export options will appear here/i)).toBeInTheDocument()
  })

  it('renders ExportCard with available PDF and PPTX exports when messages exist', () => {
    const sampleMessages = [{ id: '1', question: 'Show average glucose', report: 'Average glucose is 120.8' }]
    render(<ExportCard upload={sampleUpload} messages={sampleMessages} category="general" />)
    expect(screen.getByRole('button', { name: /PDF/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /PPTX/i })).not.toBeDisabled()
  })

  it('renders ExportCard in loading state when status is generating', () => {
    const sampleMessages = [{ id: '1', question: 'Test question', report: 'Test report' }]
    render(<ExportCard upload={sampleUpload} messages={sampleMessages} status="generating" />)
    expect(screen.getByRole('button', { name: /PDF/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /PPTX/i })).toBeDisabled()
  })

  it('renders DatasetInsightsPanel without showing error-boundary fallback when dataset has incomplete profile data', () => {
    render(<DatasetInsightsPanel upload={sampleUpload} messages={undefined} />)
    expect(screen.getByText(/Dataset Insights/i)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders TimeSeriesForecastCard without crashing even without date column', () => {
    render(<TimeSeriesForecastCard sessionId="sess-1" upload={sampleUpload} dateCol={null} />)
    expect(screen.getByText(/Time-Series Forecast/i)).toBeInTheDocument()
  })
})
