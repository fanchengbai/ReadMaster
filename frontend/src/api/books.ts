export interface ChapterSummary {
  id: string
  title: string
  order_index: number
  paragraph_count: number
}

export interface BookSummary {
  id: string
  title: string
  author: string | null
  source_filename: string
  format: 'TXT' | 'EPUB' | 'PDF'
  chapter_count: number
  progress_percentage: number
  current_chapter_id: string | null
  created_at: string
}

export interface BookDetail extends BookSummary {
  chapters: ChapterSummary[]
}

export interface ParagraphContent {
  id: string
  order_index: number
  content: string
}

export interface ChapterContent extends ChapterSummary {
  book_id: string
  paragraphs: ParagraphContent[]
}

export interface ReadingProgress {
  book_id: string
  chapter_id: string
  paragraph_id: string | null
  percentage: number
  updated_at: string | null
}

interface ApiErrorBody {
  error?: {
    message?: string
  }
}

export async function fetchBooks(): Promise<BookSummary[]> {
  const response = await fetch('/api/v1/books')
  if (!response.ok) await throwApiError(response)
  return response.json() as Promise<BookSummary[]>
}

export async function fetchBook(bookId: string): Promise<BookDetail> {
  return requestJson(`/api/v1/books/${bookId}`)
}

export async function fetchChapter(chapterId: string): Promise<ChapterContent> {
  return requestJson(`/api/v1/chapters/${chapterId}`)
}

export async function fetchProgress(bookId: string): Promise<ReadingProgress> {
  return requestJson(`/api/v1/books/${bookId}/progress`)
}

export async function saveProgress(
  bookId: string,
  progress: Pick<ReadingProgress, 'chapter_id' | 'paragraph_id' | 'percentage'>,
): Promise<ReadingProgress> {
  return requestJson(`/api/v1/books/${bookId}/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(progress),
  })
}

export async function importBook(file: File): Promise<BookDetail> {
  const body = new FormData()
  body.append('file', file)

  const response = await fetch('/api/v1/books/import', {
    method: 'POST',
    body,
  })
  if (!response.ok) await throwApiError(response)
  return response.json() as Promise<BookDetail>
}

export async function deleteBook(bookId: string): Promise<void> {
  const response = await fetch(`/api/v1/books/${bookId}`, { method: 'DELETE' })
  if (!response.ok) await throwApiError(response)
}

async function throwApiError(response: Response): Promise<never> {
  let message = '请求失败，请稍后重试'
  try {
    const body = (await response.json()) as ApiErrorBody
    message = body.error?.message || message
  } catch {
    // Keep the generic message when the server does not return JSON.
  }
  throw new Error(message)
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) await throwApiError(response)
  return response.json() as Promise<T>
}
