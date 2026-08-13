import { type FormEvent, useEffect, useState } from 'react'

import {
  type ReviewResult,
  type ReviewSession,
  type ReviewStats,
  fetchReviewSession,
  fetchReviewStats,
  submitReviewAnswer,
} from './api/review'

interface ReviewViewProps {
  onBack: () => void
  onVocabulary: () => void
}

const emptyStats: ReviewStats = {
  total_attempts: 0,
  correct_attempts: 0,
  accuracy: 0,
  words_practiced: 0,
  due_count: 0,
  scheduled_count: 0,
  next_review_at: null,
}

export default function ReviewView({ onBack, onVocabulary }: ReviewViewProps) {
  const [session, setSession] = useState<ReviewSession | null>(null)
  const [stats, setStats] = useState<ReviewStats>(emptyStats)
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<ReviewResult | null>(null)
  const [correctInSession, setCorrectInSession] = useState(0)
  const [scheduledDates, setScheduledDates] = useState<string[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    Promise.all([fetchReviewSession(), fetchReviewStats()])
      .then(([loadedSession, loadedStats]) => {
        setSession(loadedSession)
        setStats(loadedStats)
        setStatus('ready')
      })
      .catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : '无法开始训练')
        setStatus('error')
      })
  }, [])

  const question = session?.questions[index]
  const finished = Boolean(session && session.questions.length > 0 && index >= session.questions.length)

  async function submitAnswer(event?: FormEvent) {
    event?.preventDefault()
    if (!question || !answer.trim() || result) return
    setSubmitting(true)
    setMessage('')
    try {
      const reviewed = await submitReviewAnswer(question, answer)
      setResult(reviewed)
      setScheduledDates((current) => [...current, reviewed.next_review_at])
      if (reviewed.is_correct) setCorrectInSession((current) => current + 1)
      setStats((current) => ({
        total_attempts: current.total_attempts + 1,
        correct_attempts: current.correct_attempts + (reviewed.is_correct ? 1 : 0),
        words_practiced: current.words_practiced,
        due_count: Math.max(0, current.due_count - 1),
        scheduled_count: current.scheduled_count + 1,
        next_review_at: earliestDate(current.next_review_at, reviewed.next_review_at),
        accuracy: Math.round(
          ((current.correct_attempts + (reviewed.is_correct ? 1 : 0)) /
            (current.total_attempts + 1)) * 1000,
        ) / 10,
      }))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  function nextQuestion() {
    setIndex((current) => current + 1)
    setAnswer('')
    setResult(null)
    setMessage('')
  }

  return (
    <main className="review-screen">
      <header className="vocabulary-topbar">
        <button type="button" onClick={onBack}>← 返回书架</button>
        <strong>ReadMaster</strong>
      </header>
      <section className="review-header">
        <div>
          <p className="eyebrow">Context Review</p>
          <h1>词汇训练</h1>
          <p>把阅读时遇见的词，放回真实语境里重新理解。</p>
        </div>
        <div className="review-stats" aria-label="训练统计">
          <div><strong>{stats.due_count}</strong><span>今日待复习</span></div>
          <div><strong>{stats.accuracy}%</strong><span>正确率</span></div>
        </div>
      </section>

      {message && <div className="notice">{message}</div>}
      {status === 'loading' && <div className="review-empty">正在从生词库准备题目…</div>}
      {status === 'error' && <div className="review-empty">{message}</div>}
      {status === 'ready' && session?.questions.length === 0 && session.total_available === 0 && (
        <section className="review-empty">
          <div>
            <h2>还没有可以训练的生词</h2>
            <p>阅读时点击不熟悉的单词并保存，题目就会从原句中自动生成。</p>
            <button type="button" onClick={onVocabulary}>查看生词库</button>
          </div>
        </section>
      )}
      {status === 'ready' && session?.questions.length === 0 && session.total_available > 0 && (
        <section className="review-empty review-empty--scheduled">
          <div>
            <span className="review-done-mark" aria-hidden="true">✓</span>
            <h2>今天的复习已完成</h2>
            <p>
              {session.scheduled_count} 个生词正在复习计划中。
              {session.next_review_at && ` 最近一次复习安排在 ${formatReviewTime(session.next_review_at)}。`}
            </p>
            <button type="button" onClick={onBack}>返回书架</button>
          </div>
        </section>
      )}
      {status === 'ready' && question && !finished && (
        <section className="review-card">
          <div className="review-card-meta">
            <span>第 {index + 1} / {session?.questions.length} 题</span>
            <span>{question.type === 'context_fill' ? '语境填词' : '释义选择'}</span>
          </div>
          <div className="review-progress" aria-label={`本轮训练进度 ${index + 1}/${session?.questions.length}`}>
            <span style={{ width: `${((index + 1) / (session?.questions.length || 1)) * 100}%` }} />
          </div>
          <p className="review-prompt">{question.prompt}</p>
          {(question.source_book_title || question.source_chapter_title) && (
            <p className="review-source">
              来自 {question.source_book_title} · {question.source_chapter_title}
            </p>
          )}
          <form onSubmit={submitAnswer}>
            {question.type === 'meaning_choice' ? (
              <div className="review-options" role="group" aria-label="选择答案">
                {question.options.map((option) => (
                  <button
                    className={answer === option ? 'selected' : ''}
                    type="button"
                    disabled={Boolean(result)}
                    key={option}
                    onClick={() => setAnswer(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <label className="review-input">
                填写缺少的英文单词
                <input
                  autoComplete="off"
                  disabled={Boolean(result)}
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                />
              </label>
            )}
            {!result && (
              <button className="review-submit" type="submit" disabled={!answer.trim() || submitting}>
                {submitting ? '正在检查…' : '提交答案'}
              </button>
            )}
          </form>
          {result && (
            <div className={`review-result review-result--${result.is_correct ? 'correct' : 'wrong'}`} role="status">
              <strong>{result.is_correct ? '回答正确' : '再记一次'}</strong>
              <p>{result.explanation}</p>
              <button type="button" onClick={nextQuestion}>
                {index + 1 === session!.questions.length ? '查看本轮结果' : '下一题 →'}
              </button>
            </div>
          )}
        </section>
      )}
      {status === 'ready' && finished && session && (
        <section className="review-finished">
          <span aria-hidden="true">✓</span>
          <p className="eyebrow">Session Complete</p>
          <h2>本轮训练完成</h2>
          <p>共完成 {session.questions.length} 题，答对 {correctInSession} 题。</p>
          {scheduledDates.length > 0 && (
            <p>最近一项将在 {formatReviewTime(earliestScheduledDate(scheduledDates))} 再次复习。</p>
          )}
          <div>
            <button type="button" onClick={onBack}>返回书架</button>
            <button type="button" onClick={onVocabulary}>查看生词库</button>
          </div>
        </section>
      )}
    </main>
  )
}

function earliestDate(current: string | null, candidate: string): string {
  if (!current) return candidate
  return new Date(current) <= new Date(candidate) ? current : candidate
}

function earliestScheduledDate(values: string[]): string {
  return values.reduce((earliest, value) => earliestDate(earliest, value), null as string | null)!
}

function formatReviewTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
