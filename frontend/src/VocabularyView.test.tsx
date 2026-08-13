import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import VocabularyView from './VocabularyView'
import type { UserWord } from './api/vocabulary'

const word: UserWord = {
  id: 'user-word-1',
  lemma: 'curiosity',
  phonetic: '/ˌkjʊəriˈɒsəti/',
  definitions: [{ part_of_speech: 'n.', meaning: '好奇心；求知欲' }],
  provider: 'local',
  familiarity: 'new',
  encounter_count: 2,
  wrong_count: 0,
  review_stage: 0,
  consecutive_correct: 0,
  next_review_at: '2026-08-12T00:00:00Z',
  last_reviewed_at: null,
  note: null,
  first_seen_at: '2026-08-12T00:00:00Z',
  last_seen_at: '2026-08-12T00:00:00Z',
  latest_occurrence: {
    id: 'occurrence-1',
    book_id: 'book-1',
    surface_form: 'Curiosity',
    context: 'Curiosity makes reading active.',
    source_book_title: 'Reading Mind',
    source_chapter_title: 'Chapter One',
    created_at: '2026-08-12T00:00:00Z',
  },
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('shows saved context and updates familiarity', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
    if (init?.method === 'PATCH') {
      return jsonResponse({ ...word, familiarity: 'learning' })
    }
    return jsonResponse([word])
  })

  render(<VocabularyView onBack={vi.fn()} />)

  expect(await screen.findByRole('heading', { name: 'curiosity' })).toBeInTheDocument()
  expect(screen.getByText(/Curiosity makes reading active/)).toBeInTheDocument()

  fireEvent.change(screen.getByLabelText('掌握状态'), { target: { value: 'learning' } })

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/user-words/user-word-1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })
  expect(screen.getByLabelText('掌握状态')).toHaveValue('learning')
})

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
