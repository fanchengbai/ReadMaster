import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import App from './App'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('loads the local service and displays imported books', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/health')) {
      return jsonResponse({ status: 'ok', database: 'ok' })
    }
    return jsonResponse([
      {
        id: 'book-1',
        title: 'The Reading Mind',
        author: 'A. Reader',
        source_filename: 'reading-mind.txt',
        format: 'TXT',
        chapter_count: 12,
        progress_percentage: 25,
        current_chapter_id: 'chapter-1',
        created_at: '2026-08-11T00:00:00Z',
      },
    ])
  })

  render(<App />)

  expect(screen.getByRole('heading', { name: '我的书架' })).toBeInTheDocument()
  expect(await screen.findByText('本地服务已就绪')).toBeInTheDocument()
  expect(await screen.findByRole('heading', { name: 'The Reading Mind' })).toBeInTheDocument()
  expect(screen.getByText('TXT · 12 章')).toBeInTheDocument()
})

test('imports a selected EPUB file and adds it to the shelf', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/health')) return jsonResponse({ status: 'ok', database: 'ok' })
    if (url.endsWith('/books/import')) {
      return jsonResponse(
        {
          id: 'book-2',
          title: 'New EPUB Book',
          author: null,
          source_filename: 'new-book.epub',
          format: 'EPUB',
          chapter_count: 2,
          progress_percentage: 0,
          current_chapter_id: null,
          created_at: '2026-08-11T00:00:00Z',
          chapters: [],
        },
        201,
      )
    }
    return jsonResponse([])
  })

  render(<App />)
  const input = screen.getByLabelText('选择 TXT 或 EPUB 文件')
  const file = new File(['epub-content'], 'new-book.epub', { type: 'application/epub+zip' })

  fireEvent.change(input, { target: { files: [file] } })

  expect(await screen.findByText('《New EPUB Book》导入成功')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'New EPUB Book' })).toBeInTheDocument()
  expect(screen.getByText('EPUB · 2 章')).toBeInTheDocument()
})

test('opens the review area from the main navigation', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/health')) return jsonResponse({ status: 'ok', database: 'ok' })
    if (url.includes('/review/session')) return jsonResponse({ total_available: 0, questions: [] })
    if (url.endsWith('/review/stats')) {
      return jsonResponse({ total_attempts: 0, correct_attempts: 0, accuracy: 0, words_practiced: 0 })
    }
    return jsonResponse([])
  })

  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: '训练' }))

  expect(await screen.findByRole('heading', { name: '词汇训练' })).toBeInTheDocument()
  expect(await screen.findByRole('heading', { name: '还没有可以训练的生词' })).toBeInTheDocument()
})

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
