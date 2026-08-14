import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import ReviewView from './ReviewView'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('moves through five gates and saves the completed journey', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.includes('/review/session')) {
      return jsonResponse({
        total_available: 1,
        due_count: 1,
        scheduled_count: 0,
        next_review_at: null,
        questions: [{
          id: 'word-1',
          type: 'context_fill',
          prompt: '_____ makes reading active.',
          options: [],
          lemma: 'curiosity',
          phonetic: 'ˌkjʊəriˈɒsəti',
          meanings: ['好奇心'],
          context: 'Curiosity makes reading active.',
          source_book_title: 'Reading Mind',
          source_chapter_title: 'Chapter One',
        }],
      })
    }
    if (url.endsWith('/review/stats')) {
      return jsonResponse({
        total_attempts: 2,
        correct_attempts: 1,
        accuracy: 50,
        words_practiced: 1,
        due_count: 1,
        scheduled_count: 0,
        next_review_at: null,
      })
    }
    if (url.endsWith('/review/complete') && init?.method === 'POST') {
      return jsonResponse({
        completed_count: 1,
        repaired_count: 0,
        next_review_at: '2026-08-14T00:00:00Z',
      })
    }
    return jsonResponse({}, 404)
  })

  render(<ReviewView onBack={vi.fn()} onVocabulary={vi.fn()} />)

  await screen.findByText('第 1 关 · 初次认词')
  completeChoice('认识这个词')
  advancePassedGate()

  await screen.findByText('第 2 关 · 释义辨别')
  completeChoice('好奇心')
  advancePassedGate()

  await screen.findByText('第 3 关 · 语境选词')
  completeChoice('curiosity')
  advancePassedGate()

  await screen.findByText('第 4 关 · 独立拼写')
  completeInput('填写缺少的英文单词', 'curiosity')
  advancePassedGate()

  await screen.findByText('第 5 关 · 主动回想')
  completeInput('填写对应的英文单词', 'curiosity')
  fireEvent.click(await screen.findByRole('button', { name: '完成训练' }))

  expect(await screen.findByRole('heading', { name: '五关全部完成' })).toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/review/complete',
    expect.objectContaining({ method: 'POST' }),
  ))
})

function completeChoice(answer: string) {
  fireEvent.click(screen.getByRole('button', { name: answer }))
  fireEvent.click(screen.getByRole('button', { name: '确认答案' }))
  fireEvent.click(screen.getByRole('button', { name: '查看本关结果' }))
}

function completeInput(label: string, answer: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value: answer } })
  fireEvent.click(screen.getByRole('button', { name: '确认答案' }))
  fireEvent.click(screen.getByRole('button', { name: '查看本关结果' }))
}

function advancePassedGate() {
  fireEvent.click(screen.getByRole('button', { name: '进入下一关' }))
}

test('guides the reader to save words when no questions exist', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/review/session')) {
      return jsonResponse({
        total_available: 0,
        due_count: 0,
        scheduled_count: 0,
        next_review_at: null,
        questions: [],
      })
    }
    return jsonResponse({
      total_attempts: 0,
      correct_attempts: 0,
      accuracy: 0,
      words_practiced: 0,
      due_count: 0,
      scheduled_count: 0,
      next_review_at: null,
    })
  })
  const onVocabulary = vi.fn()

  render(<ReviewView onBack={vi.fn()} onVocabulary={onVocabulary} />)

  expect(await screen.findByRole('heading', { name: '还没有可以训练的生词' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '查看生词库' }))
  expect(onVocabulary).toHaveBeenCalledOnce()
})

test('shows the next scheduled time when nothing is due today', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/review/session')) {
      return jsonResponse({
        total_available: 2,
        due_count: 0,
        scheduled_count: 2,
        next_review_at: '2026-08-14T08:00:00Z',
        questions: [],
      })
    }
    return jsonResponse({
      total_attempts: 3,
      correct_attempts: 2,
      accuracy: 66.7,
      words_practiced: 2,
      due_count: 0,
      scheduled_count: 2,
      next_review_at: '2026-08-14T08:00:00Z',
    })
  })

  render(<ReviewView onBack={vi.fn()} onVocabulary={vi.fn()} />)

  expect(await screen.findByRole('heading', { name: '今天的复习已完成' })).toBeInTheDocument()
  expect(screen.getByText(/2 个生词正在复习计划中/)).toBeInTheDocument()
})

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
