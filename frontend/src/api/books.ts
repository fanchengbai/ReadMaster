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
  chapter_count: number
  created_at: string
}

export interface BookDetail extends BookSummary {
  chapters: ChapterSummary[]
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

export async function importTxtBook(file: File): Promise<BookDetail> {
  const body = new FormData()
  body.append('file', file)

  const response = await fetch('/api/v1/books/import', {
    method: 'POST',
    body,
  })
  if (!response.ok) await throwApiError(response)
  return response.json() as Promise<BookDetail>
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
