export type Familiarity = 'new' | 'learning' | 'familiar' | 'mastered'

export interface Definition {
  part_of_speech: string
  meaning: string
}

export interface DictionaryEntry {
  lemma: string
  surface_form: string
  phonetic: string | null
  definitions: Definition[]
  provider: string
  found: boolean
  saved: boolean
}

export interface WordOccurrence {
  id: string
  book_id: string | null
  surface_form: string
  context: string
  source_book_title: string
  source_chapter_title: string
  created_at: string
}

export interface UserWord {
  id: string
  lemma: string
  phonetic: string | null
  definitions: Definition[]
  provider: string | null
  familiarity: Familiarity
  encounter_count: number
  wrong_count: number
  note: string | null
  first_seen_at: string
  last_seen_at: string
  latest_occurrence: WordOccurrence | null
}

export interface WordSelection {
  word: string
  book_id: string
  chapter_id: string
  paragraph_id: string
  char_start: number
  char_end: number
}

export async function lookupWord(word: string): Promise<DictionaryEntry> {
  return requestJson(`/api/v1/dictionary/${encodeURIComponent(word)}`)
}

export async function saveUserWord(selection: WordSelection): Promise<UserWord> {
  return requestJson('/api/v1/user-words', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(selection),
  })
}

export async function fetchUserWords(familiarity?: Familiarity): Promise<UserWord[]> {
  const query = familiarity ? `?familiarity=${familiarity}` : ''
  return requestJson(`/api/v1/user-words${query}`)
}

export async function updateUserWord(
  id: string,
  update: { familiarity?: Familiarity; note?: string },
): Promise<UserWord> {
  return requestJson(`/api/v1/user-words/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
}

export async function removeUserWord(id: string): Promise<void> {
  const response = await fetch(`/api/v1/user-words/${id}`, { method: 'DELETE' })
  if (!response.ok) await throwApiError(response)
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) await throwApiError(response)
  return response.json() as Promise<T>
}

async function throwApiError(response: Response): Promise<never> {
  let message = '请求失败，请稍后重试'
  try {
    const body = (await response.json()) as { error?: { message?: string } }
    message = body.error?.message || message
  } catch {
    // Keep the generic fallback when no structured error is returned.
  }
  throw new Error(message)
}
