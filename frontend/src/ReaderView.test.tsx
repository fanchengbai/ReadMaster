import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import ReaderView from './ReaderView'

const book = {
  id: 'book-1',
  title: 'The Reading Mind',
  author: 'Jane Reader',
  source_filename: 'reading.epub',
  format: 'EPUB' as const,
  chapter_count: 2,
  progress_percentage: 0,
  current_chapter_id: null,
  created_at: '2026-08-12T00:00:00Z',
  chapters: [
    { id: 'chapter-1', title: 'A Beginning', order_index: 0, paragraph_count: 1 },
    { id: 'chapter-2', title: 'Practice', order_index: 1, paragraph_count: 1 },
  ],
}

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

test('opens the saved chapter and moves to the next chapter', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/books/book-1')) return jsonResponse(book)
    if (url.endsWith('/books/book-1/progress') && init?.method !== 'PUT') {
      return jsonResponse({
        book_id: 'book-1',
        chapter_id: 'chapter-1',
        paragraph_id: null,
        percentage: 0,
        updated_at: null,
      })
    }
    if (url.endsWith('/chapters/chapter-1')) {
      return jsonResponse({
        ...book.chapters[0],
        book_id: 'book-1',
        paragraphs: [{ id: 'paragraph-1', order_index: 0, content: 'Reading starts here.' }],
      })
    }
    if (url.endsWith('/chapters/chapter-2')) {
      return jsonResponse({
        ...book.chapters[1],
        book_id: 'book-1',
        paragraphs: [{ id: 'paragraph-2', order_index: 0, content: 'Practice builds skill.' }],
      })
    }
    return jsonResponse({
      book_id: 'book-1',
      chapter_id: 'chapter-1',
      paragraph_id: 'paragraph-1',
      percentage: 50,
      updated_at: '2026-08-12T00:00:00Z',
    })
  })

  render(<ReaderView bookId="book-1" onClose={vi.fn()} onProgressChange={vi.fn()} />)

  expect(await screen.findByRole('heading', { name: 'A Beginning' })).toBeInTheDocument()
  expect(screen.getByText('Reading starts here.')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '下一章 →' }))

  expect(await screen.findByRole('heading', { name: 'Practice' })).toBeInTheDocument()
  expect(screen.getByText('Practice builds skill.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '下一章 →' })).toBeDisabled()
})

test('stores reader display settings locally', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/books/book-1')) return jsonResponse(book)
    if (url.endsWith('/progress')) {
      return jsonResponse({
        book_id: 'book-1',
        chapter_id: 'chapter-1',
        paragraph_id: null,
        percentage: 0,
        updated_at: null,
      })
    }
    return jsonResponse({
      ...book.chapters[0],
      book_id: 'book-1',
      paragraphs: [{ id: 'paragraph-1', order_index: 0, content: 'Reading starts here.' }],
    })
  })

  render(<ReaderView bookId="book-1" onClose={vi.fn()} onProgressChange={vi.fn()} />)
  await screen.findByRole('heading', { name: 'A Beginning' })
  fireEvent.click(screen.getByRole('button', { name: '阅读设置' }))
  fireEvent.change(screen.getByLabelText('字号'), { target: { value: '24' } })
  fireEvent.click(screen.getByRole('button', { name: '夜间' }))

  expect(localStorage.getItem('readmaster.reader-settings')).toContain('"fontSize":24')
  expect(localStorage.getItem('readmaster.reader-settings')).toContain('"theme":"night"')
})

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
