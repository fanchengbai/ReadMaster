import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import ReviewView from './ReviewView'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('submits a context answer and completes the review session', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.includes('/review/session')) {
      return jsonResponse({
        total_available: 1,
        questions: [{
          id: 'word-1',
          type: 'context_fill',
          prompt: '_____ makes reading active.',
          options: [],
          source_book_title: 'Reading Mind',
          source_chapter_title: 'Chapter One',
        }],
      })
    }
    if (url.endsWith('/review/stats')) {
      return jsonResponse({ total_attempts: 2, correct_attempts: 1, accuracy: 50, words_practiced: 1 })
    }
    if (url.endsWith('/review/answer') && init?.method === 'POST') {
      return jsonResponse({
        is_correct: true,
        correct_answer: 'curiosity',
        explanation: '回答正确，已经完成这次巩固。',
        wrong_count: 0,
        answered_at: '2026-08-13T00:00:00Z',
      })
    }
    return jsonResponse({}, 404)
  })

  render(<ReviewView onBack={vi.fn()} onVocabulary={vi.fn()} />)

  const input = await screen.findByLabelText('填写缺少的英文单词')
  fireEvent.change(input, { target: { value: 'curiosity' } })
  fireEvent.click(screen.getByRole('button', { name: '提交答案' }))

  expect(await screen.findByText('回答正确')).toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/review/answer',
    expect.objectContaining({ method: 'POST' }),
  ))

  fireEvent.click(screen.getByRole('button', { name: '查看本轮结果' }))
  expect(screen.getByRole('heading', { name: '本轮训练完成' })).toBeInTheDocument()
  expect(screen.getByText('共完成 1 题，答对 1 题。')).toBeInTheDocument()
})

test('guides the reader to save words when no questions exist', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/review/session')) {
      return jsonResponse({ total_available: 0, questions: [] })
    }
    return jsonResponse({ total_attempts: 0, correct_attempts: 0, accuracy: 0, words_practiced: 0 })
  })
  const onVocabulary = vi.fn()

  render(<ReviewView onBack={vi.fn()} onVocabulary={onVocabulary} />)

  expect(await screen.findByRole('heading', { name: '还没有可以训练的生词' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '查看生词库' }))
  expect(onVocabulary).toHaveBeenCalledOnce()
})

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
