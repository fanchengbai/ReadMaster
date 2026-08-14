export type QuestionType = 'context_fill' | 'meaning_choice'

export interface ReviewQuestion {
  id: string
  type: QuestionType
  prompt: string
  options: string[]
  lemma: string
  phonetic: string | null
  meanings: string[]
  context: string
  source_book_title: string | null
  source_chapter_title: string | null
}

export interface ReviewSession {
  questions: ReviewQuestion[]
  total_available: number
  due_count: number
  scheduled_count: number
  next_review_at: string | null
}

export interface ReviewResult {
  is_correct: boolean
  correct_answer: string
  explanation: string
  wrong_count: number
  review_stage: number
  next_review_at: string
  answered_at: string
}

export interface ReviewStats {
  total_attempts: number
  correct_attempts: number
  accuracy: number
  words_practiced: number
  due_count: number
  scheduled_count: number
  next_review_at: string | null
}

export interface GateReviewCompletion {
  completed_count: number
  repaired_count: number
  next_review_at: string
}

export async function fetchReviewSession(limit = 10): Promise<ReviewSession> {
  return requestJson(`/api/v1/review/session?limit=${limit}`)
}

export async function fetchReviewStats(): Promise<ReviewStats> {
  return requestJson('/api/v1/review/stats')
}

export async function submitReviewAnswer(
  question: ReviewQuestion,
  answer: string,
): Promise<ReviewResult> {
  return requestJson('/api/v1/review/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: question.id,
      question_type: question.type,
      prompt: question.prompt,
      answer,
    }),
  })
}

export async function completeGateReview(
  questions: ReviewQuestion[],
  mistakeCounts: Record<string, number>,
): Promise<GateReviewCompletion> {
  return requestJson('/api/v1/review/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: questions.map((question) => ({
        question_id: question.id,
        mistake_count: mistakeCounts[question.id] || 0,
      })),
    }),
  })
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let message = '训练请求失败，请稍后重试'
    try {
      const body = (await response.json()) as { error?: { message?: string } }
      message = body.error?.message || message
    } catch {
      // Keep the generic fallback when the service returns no structured error.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}
