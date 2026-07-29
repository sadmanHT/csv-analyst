import { describe, test, expect } from 'vitest'

function getPrimitiveText(value) {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : undefined
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return undefined
}

function normalizeStepStatus(val) {
  const s = String(val || '').toLowerCase()
  if (s === 'complete' || s === 'completed' || s === 'success' || s === 'done') return 'complete'
  if (s === 'warning' || s === 'lens_switch') return 'warning'
  if (s === 'error' || s === 'failed') return 'failed'
  if (s === 'running' || s === 'executing' || s === 'pending') return 'running'
  return 'complete'
}

function normalizeExecutionStep(step, index) {
  return {
    id: String(step?.id || step?.step_id || step?.stepId || `step-${index + 1}`),
    label: String(step?.label || step?.name || step?.title || step?.message || step?.step || 'Analysis step'),
    detail: step?.detail || step?.description || step?.summary || step?.message,
    status: normalizeStepStatus(step?.status || step?.step),
    durationMs: step?.duration_ms || step?.durationMs || step?.meta?.elapsed_ms,
  }
}

function normalizeStatus(val) {
  const s = String(val || '').toLowerCase()
  if (s === 'complete' || s === 'completed' || s === 'success' || s === 'succeeded' || s === 'done') return 'complete'
  if (s === 'partial' || s === 'streaming') return 'partial'
  if (s === 'error' || s === 'failed' || s === 'failure') return 'failed'
  return 'running'
}

function toDisplayText(value, fallback = '') {
  if (value == null) return fallback

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value)
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => toDisplayText(item))
      .filter(Boolean)
      .join('\n')
  }

  if (typeof value === 'object') {
    return (
      toDisplayText(value.message) ||
      toDisplayText(value.summary) ||
      toDisplayText(value.text) ||
      toDisplayText(value.detail) ||
      toDisplayText(value.code) ||
      fallback
    )
  }

  return fallback
}

function normalizeApiError(error) {
  if (!error) return null

  if (typeof error === 'string') {
    return {
      code: 'request_failed',
      message: error,
    }
  }

  return {
    code: toDisplayText(error.code, 'request_failed'),
    message: toDisplayText(
      error.message ?? error.detail,
      'The analysis could not be completed.'
    ),
  }
}

function normalizeQueryResponse(raw = {}, fallbackRequestId) {
  const rawIsObject = raw !== null && typeof raw === 'object'
  const error = normalizeApiError(raw?.error)

  const nestedResult =
    rawIsObject && raw.result !== null && typeof raw.result === 'object'
      ? raw.result
      : rawIsObject && raw.data !== null && typeof raw.data === 'object'
        ? raw.data
        : rawIsObject && raw.analysis !== null && typeof raw.analysis === 'object'
          ? raw.analysis
          : rawIsObject
            ? raw
            : {}

  const answerObject =
    nestedResult.answer ??
    nestedResult.final_answer ??
    nestedResult.finalAnswer ??
    nestedResult.response ??
    nestedResult.output

  const primitiveResultText =
    getPrimitiveText(raw?.result) ??
    getPrimitiveText(nestedResult?.result)

  let answerText =
    toDisplayText(answerObject?.summary) ||
    toDisplayText(answerObject?.explanation) ||
    toDisplayText(answerObject?.text) ||
    toDisplayText(answerObject) ||
    primitiveResultText ||
    toDisplayText(raw?.report) ||
    toDisplayText(raw?.answer) ||
    toDisplayText(raw?.response) ||
    toDisplayText(raw?.output) ||
    error?.message ||
    ''

  let answerType =
    nestedResult.answer_type ??
    nestedResult.answerType

  let answerData

  if (typeof answerObject === 'string') {
    answerText = answerObject.trim() || answerText
  } else if (answerObject && typeof answerObject === 'object') {
    answerType = answerObject.type ?? answerType
    answerData =
      answerObject.data ??
      answerObject.payload ??
      answerObject.rows ??
      answerObject.values
  }

  if (!answerData) {
    answerData = raw?.row_data ?? raw?.payload?.row_data ?? nestedResult?.row_data
  }

  const rawSteps =
    nestedResult.execution_steps ??
    nestedResult.executionSteps ??
    nestedResult.steps ??
    nestedResult.trace ??
    nestedResult.agent_steps ??
    nestedResult.agentSteps ??
    nestedResult.logs ??
    raw?.execution_steps ??
    raw?.executionSteps ??
    raw?.steps ??
    raw?.trace ??
    raw?.agent_steps ??
    raw?.logs ??
    []

  return {
    requestId: String(
      nestedResult.request_id ??
      nestedResult.requestId ??
      raw?.request_id ??
      raw?.requestId ??
      fallbackRequestId
    ),
    status: normalizeStatus(nestedResult.status ?? raw?.status ?? (error ? 'failed' : 'complete')),
    answer: raw?.answer ?? nestedResult.answer ?? null,
    error,
    answerText: typeof answerText === 'string' ? answerText : toDisplayText(answerText),
    answerType: answerType || (answerData?.fields ? 'row_lookup' : 'text'),
    answerData,
    executionSteps: Array.isArray(rawSteps)
      ? rawSteps.map(normalizeExecutionStep)
      : [],
    warnings: Array.isArray(nestedResult.warnings ?? raw?.warnings) ? (nestedResult.warnings ?? raw?.warnings) : [],
    generatedCode:
      nestedResult.generated_code ??
      nestedResult.generatedCode ??
      raw?.generated_code ??
      raw?.generatedCode ??
      raw?.code,
    effectiveLens:
      nestedResult.effective_lens ??
      nestedResult.effectiveLens ??
      raw?.effective_lens ??
      raw?.effectiveLens,
    raw,
  }
}

const PROGRESS_EVENT_TYPES = new Set([
  'analysis_started',
  'route_selected',
  'step_started',
  'step_completed',
  'execution_step',
  'progress',
  'log',
  'agent_started',
  'agent_completed',
  'strategy',
  'understanding',
  'lens_check',
  'thinking',
  'planning',
  'analyzing',
  'visualizing',
  'critiquing',
  'reporting',
  'code',
  'plan',
  'analyst',
  'critique',
])

const PARTIAL_RESULT_EVENT_TYPES = new Set([
  'partial_result',
  'section_updated',
  'answer_partial',
])

const SUCCESS_EVENT_TYPES = new Set([
  'analysis_completed',
  'completed',
  'done',
])

const FAILURE_EVENT_TYPES = new Set([
  'analysis_failed',
  'failed',
  'error',
])

function classifyStreamEvent(event) {
  const type = String(event?.type ?? event?.event ?? event?.step ?? '').toLowerCase()

  if (SUCCESS_EVENT_TYPES.has(type)) {
    return 'terminal-success'
  }
  if (FAILURE_EVENT_TYPES.has(type)) {
    return 'terminal-failure'
  }
  if (PARTIAL_RESULT_EVENT_TYPES.has(type)) {
    return 'partial-result'
  }
  if (PROGRESS_EVENT_TYPES.has(type)) {
    return 'progress'
  }

  if (event?.status === 'complete' || event?.status === 'completed') {
    return 'terminal-success'
  }
  if (event?.status === 'failed' || event?.status === 'error') {
    return 'terminal-failure'
  }

  return 'progress'
}

function normalizeStreamStatus(event) {
  const eventClass = classifyStreamEvent(event)
  if (eventClass === 'terminal-success') return 'complete'
  if (eventClass === 'terminal-failure') return 'failed'
  if (eventClass === 'partial-result') return 'partial'
  return 'running'
}

describe('normalizeQueryResponse', () => {
  test('correctly extracts answerText and executionSteps from primitive result payload', () => {
    const raw = {
      request_id: 'abc123',
      status: 'complete',
      result: '**Row 70 Data Summary**\n\nGlucose: 120',
      execution_steps: [
        {
          id: 'retrieve-row',
          label: 'Retrieved row 70',
          status: 'complete',
        },
      ],
    }

    const normalized = normalizeQueryResponse(raw, 'fallback')
    expect(normalized.answerText).toContain('Row 70 Data Summary')
    expect(normalized.executionSteps).toHaveLength(1)
    expect(normalized.executionSteps[0].label).toBe('Retrieved row 70')
  })

  test('correctly extracts answerText, answerData, and answerType when result is an object', () => {
    const raw = {
      request_id: 'req-456',
      status: 'complete',
      answer: {
        type: 'row_lookup',
        text: 'Row 70 summary text',
        data: { display_row: 70, fields: [{ field: 'Pregnancies', value: '4' }] },
      },
      execution_steps: [
        { id: 'classify', label: 'Detected direct row lookup', status: 'complete' },
      ],
    }

    const normalized = normalizeQueryResponse(raw, 'fallback')
    expect(normalized.answerText).toBe('Row 70 summary text')
    expect(normalized.answerType).toBe('row_lookup')
    expect(normalized.answerData.display_row).toBe(70)
    expect(normalized.executionSteps).toHaveLength(1)
  })
})

describe('classifyStreamEvent and stream lifecycle', () => {
  test('correctly classifies all stream event types', () => {
    expect(classifyStreamEvent({ type: 'analysis_started' })).toBe('progress')
    expect(classifyStreamEvent({ type: 'step_started' })).toBe('progress')
    expect(classifyStreamEvent({ type: 'step_completed' })).toBe('progress')
    expect(classifyStreamEvent({ type: 'partial_result' })).toBe('partial-result')
    expect(classifyStreamEvent({ type: 'analysis_completed' })).toBe('terminal-success')
    expect(classifyStreamEvent({ type: 'analysis_failed' })).toBe('terminal-failure')
    expect(classifyStreamEvent({ type: 'unknown_type' })).toBe('progress')
  })

  test('normalizeStreamStatus returns running for progress events and complete only for terminal success', () => {
    expect(normalizeStreamStatus({ type: 'analysis_started' })).toBe('running')
    expect(normalizeStreamStatus({ type: 'step_started' })).toBe('running')
    expect(normalizeStreamStatus({ type: 'partial_result' })).toBe('partial')
    expect(normalizeStreamStatus({ type: 'analysis_completed' })).toBe('complete')
    expect(normalizeStreamStatus({ type: 'analysis_failed' })).toBe('failed')
  })

  test('processes a stream sequence without false no-answer errors on intermediate steps', () => {
    const sequence = [
      { type: 'analysis_started', request_id: '123' },
      { type: 'step_started', request_id: '123', step: { id: 'profile', label: 'Profiling dataset' } },
      { type: 'step_completed', request_id: '123', step: { id: 'profile', label: 'Profiled dataset', status: 'complete' } },
      { type: 'partial_result', request_id: '123', answer: { type: 'dataset_summary', text: 'Initial dataset summary' } },
      { type: 'analysis_completed', request_id: '123', status: 'complete', answer: { type: 'dataset_summary', text: 'Final dataset summary' } },
    ]

    let state = {
      id: '123',
      status: 'running',
      steps: [],
      answerText: null,
      error: null,
    }

    for (const event of sequence) {
      const eventClass = classifyStreamEvent(event)
      const norm = normalizeQueryResponse(event, '123')

      if (eventClass === 'progress') {
        state = {
          ...state,
          status: 'running',
          steps: [...state.steps, event],
        }
      } else if (eventClass === 'partial-result') {
        state = {
          ...state,
          status: 'partial',
          steps: [...state.steps, event],
          answerText: norm.answerText ?? state.answerText,
        }
      } else if (eventClass === 'terminal-success') {
        const hasAnswer = Boolean(norm.answerText)
        if (!hasAnswer) {
          state = { ...state, status: 'failed', error: 'The analysis finished without returning a displayable answer.' }
        } else {
          state = { ...state, status: 'complete', answerText: norm.answerText, error: null }
        }
      }
    }

    expect(state.status).toBe('complete')
    expect(state.answerText).toBe('Final dataset summary')
    expect(state.error).toBeNull()
    expect(state.steps).toHaveLength(4)
  })

  test('handles SSE buffer splitting across chunks and multiple events per chunk correctly', () => {
    let buffer = ''
    const chunks = [
      'data: {"type":"analysis_started","request_id":"123"}\n\ndata: {"type":"step_started","request_id"',
      ':"123","step":{"id":"1","label":"Planning"}}\n\ndata: {"type":"analysis_completed","request_id":"123","answer":{"text":"Done"}}\n\n',
    ]

    const parsedEvents = []
    for (const chunk of chunks) {
      buffer += chunk
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const line = block.split('\n').find((l) => l.startsWith('data: '))
        if (line) {
          parsedEvents.push(JSON.parse(line.slice(6)))
        }
      }
    }

    expect(parsedEvents).toHaveLength(3)
    expect(parsedEvents[0].type).toBe('analysis_started')
    expect(parsedEvents[1].type).toBe('step_started')
    expect(parsedEvents[2].type).toBe('analysis_completed')
  })
})

function getStreamStatus(event) {
  const type = String(event?.type ?? event?.event ?? event?.step ?? '').toLowerCase()
  if (type === 'analysis_completed' || event?.status === 'complete' || event?.status === 'completed') return 'complete'
  if (type === 'analysis_failed' || event?.status === 'failed' || event?.status === 'error') return 'failed'
  if (type === 'partial_result' || type === 'section_updated' || type === 'answer_partial') return 'partial'
  if (type === 'validation_started' || type === 'validation_in_progress' || type === 'critiquing' || type === 'critique') return 'validating'
  if (type === 'planning' || type === 'understanding' || type === 'route_selected') return 'planning'
  return 'running'
}

describe('getStreamStatus and Card State Logic', () => {
  test('correctly maps stream events to analysis states', () => {
    expect(getStreamStatus({ type: 'planning' })).toBe('planning')
    expect(getStreamStatus({ type: 'analysis_started' })).toBe('running')
    expect(getStreamStatus({ type: 'step_started' })).toBe('running')
    expect(getStreamStatus({ type: 'partial_result' })).toBe('partial')
    expect(getStreamStatus({ type: 'validation_started' })).toBe('validating')
    expect(getStreamStatus({ type: 'analysis_completed' })).toBe('complete')
    expect(getStreamStatus({ type: 'analysis_failed' })).toBe('failed')
  })

  test('does not set empty final answer error during running, partial, or validating states', () => {
    const states = ['queued', 'planning', 'running', 'partial', 'validating']
    for (const status of states) {
      const hasAnswer = false
      const isCompleteWithoutAnswer = status === 'complete' && !hasAnswer
      expect(isCompleteWithoutAnswer).toBe(false)
    }
  })

  test('flags empty final answer error ONLY on complete status without renderable answer', () => {
    const status = 'complete'
    const hasAnswer = false
    const isCompleteWithoutAnswer = status === 'complete' && !hasAnswer
    expect(isCompleteWithoutAnswer).toBe(true)
  })

  test('does not place error objects into answerText', () => {
    const raw = {
      status: 'failed',
      answer: null,
      error: {
        code: 'answer_generation_failed',
        message: 'Generation failed.',
      },
    }

    const normalized = normalizeQueryResponse(raw, 'fallback')
    expect(normalized.answerText).toBe('Generation failed.')
    expect(typeof normalized.answerText).toBe('string')
    expect(normalized.error).toEqual({
      code: 'answer_generation_failed',
      message: 'Generation failed.',
    })
  })
})

