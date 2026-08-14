import { type FormEvent, useEffect, useMemo, useState } from 'react'

import {
  type GateReviewCompletion,
  type ReviewQuestion,
  type ReviewSession,
  type ReviewStats,
  completeGateReview,
  fetchReviewSession,
  fetchReviewStats,
} from './api/review'

interface ReviewViewProps {
  onBack: () => void
  onVocabulary: () => void
}

interface GateDefinition {
  name: string
  method: string
  shortName: string
}

interface GateTask {
  answerLabel: string
  correctAnswer: string
  detail: string
  mode: 'choice' | 'input'
  options: string[]
  prompt: string
}

interface GateOutcome {
  missedIds: string[]
  score: number
}

const gates: GateDefinition[] = [
  { shortName: '认词', name: '初次认词', method: '看单词、音标、释义和原句，建立第一印象' },
  { shortName: '辨义', name: '释义辨别', method: '从选项中找出单词的核心含义' },
  { shortName: '语境', name: '语境选词', method: '把单词放回第一次遇见它的原句' },
  { shortName: '拼写', name: '独立拼写', method: '根据原句写出缺少的英文单词' },
  { shortName: '回想', name: '主动回想', method: '只看中文含义，独立回想英文' },
]

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
  const [gateIndex, setGateIndex] = useState(0)
  const [roundIds, setRoundIds] = useState<string[]>([])
  const [itemIndex, setItemIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<{ correct: boolean; text: string } | null>(null)
  const [roundCorrect, setRoundCorrect] = useState(0)
  const [roundMissed, setRoundMissed] = useState<string[]>([])
  const [mistakeCounts, setMistakeCounts] = useState<Record<string, number>>({})
  const [outcome, setOutcome] = useState<GateOutcome | null>(null)
  const [repairMode, setRepairMode] = useState(false)
  const [initialScores, setInitialScores] = useState<Record<number, number>>({})
  const [completion, setCompletion] = useState<GateReviewCompletion | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    Promise.all([fetchReviewSession(8), fetchReviewStats()])
      .then(([loadedSession, loadedStats]) => {
        setSession(loadedSession)
        setStats(loadedStats)
        setRoundIds(loadedSession.questions.map((question) => question.id))
        setStatus('ready')
      })
      .catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : '无法开始训练')
        setStatus('error')
      })
  }, [])

  const questionsById = useMemo(
    () => new Map(session?.questions.map((question) => [question.id, question]) || []),
    [session],
  )
  const question = questionsById.get(roundIds[itemIndex])
  const task = useMemo(
    () => question && buildGateTask(question, gateIndex, session?.questions || []),
    [gateIndex, question, session?.questions],
  )
  const progress = roundIds.length ? ((itemIndex + 1) / roundIds.length) * 100 : 0

  function submitAnswer(event?: FormEvent) {
    event?.preventDefault()
    if (!question || !task || !answer.trim() || feedback) return
    const correct = normalizeAnswer(answer) === normalizeAnswer(task.correctAnswer)
    if (correct) {
      setRoundCorrect((current) => current + 1)
      setFeedback({ correct: true, text: gateIndex === 0 ? '很好，继续巩固。' : '回答正确。' })
    } else {
      setRoundMissed((current) => addUnique(current, question.id))
      setMistakeCounts((current) => ({
        ...current,
        [question.id]: (current[question.id] || 0) + 1,
      }))
      setFeedback({
        correct: false,
        text: gateIndex === 0
          ? '先看一遍释义和原句，这个词会进入本关修正。'
          : `正确答案是“${task.correctAnswer}”。`,
      })
    }
  }

  function nextTask() {
    if (itemIndex + 1 < roundIds.length) {
      setItemIndex((current) => current + 1)
      setAnswer('')
      setFeedback(null)
      return
    }

    const score = roundIds.length ? Math.round((roundCorrect / roundIds.length) * 100) : 0
    if (!repairMode) {
      setInitialScores((current) => ({ ...current, [gateIndex]: score }))
    }
    setOutcome({ score: repairMode ? initialScores[gateIndex] ?? score : score, missedIds: roundMissed })
    setAnswer('')
    setFeedback(null)
  }

  function beginRepair(ids: string[]) {
    setRepairMode(true)
    resetRound(ids)
  }

  function resetRound(ids: string[]) {
    setRoundIds(ids)
    setItemIndex(0)
    setRoundCorrect(0)
    setRoundMissed([])
    setAnswer('')
    setFeedback(null)
    setOutcome(null)
  }

  function enterNextGate() {
    if (!session) return
    setRepairMode(false)
    setGateIndex((current) => current + 1)
    resetRound(session.questions.map((item) => item.id))
  }

  async function finishTraining() {
    if (!session || submitting) return
    setSubmitting(true)
    setMessage('')
    try {
      const completed = await completeGateReview(session.questions, mistakeCounts)
      setCompletion(completed)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '训练结果保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  function outcomeAction() {
    if (!outcome) return
    if (outcome.missedIds.length > 0) {
      beginRepair(outcome.missedIds)
    } else if (gateIndex < gates.length - 1) {
      enterNextGate()
    } else {
      void finishTraining()
    }
  }

  return (
    <main className="review-screen">
      <header className="vocabulary-topbar">
        <button type="button" onClick={onBack}>← 返回书架</button>
        <strong>ReadMaster</strong>
      </header>

      <section className="review-header review-header--gates">
        <div>
          <p className="eyebrow">Vocabulary Journey</p>
          <h1>词汇闯关</h1>
          <p>先认出，再理解，最后独立回想。</p>
        </div>
        <div className="review-stats" aria-label="训练统计">
          <div><strong>{stats.due_count}</strong><span>今日待复习</span></div>
          <div><strong>{stats.accuracy}%</strong><span>历史正确率</span></div>
        </div>
      </section>

      {message && <div className="notice">{message}</div>}
      {status === 'loading' && <div className="review-empty">正在从生词库准备关卡…</div>}
      {status === 'error' && <div className="review-empty">{message}</div>}
      {status === 'ready' && session?.questions.length === 0 && session.total_available === 0 && (
        <section className="review-empty">
          <div>
            <h2>还没有可以训练的生词</h2>
            <p>阅读时点击不熟悉的单词并保存，系统会为它生成五个训练关卡。</p>
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

      {status === 'ready' && session && session.questions.length > 0 && !completion && (
        <>
          <ol className="review-gate-map" aria-label="词汇训练关卡">
            {gates.map((gate, index) => (
              <li
                className={index < gateIndex ? 'completed' : index === gateIndex ? 'active' : ''}
                key={gate.shortName}
                aria-current={index === gateIndex ? 'step' : undefined}
              >
                <span>{index < gateIndex ? '✓' : index + 1}</span>
                <strong>{gate.shortName}</strong>
              </li>
            ))}
          </ol>

          {outcome ? (
            <GateOutcomeView
              gate={gates[gateIndex]}
              outcome={outcome}
              repairMode={repairMode}
              submitting={submitting}
              finalGate={gateIndex === gates.length - 1}
              onContinue={outcomeAction}
            />
          ) : question && task ? (
            <section className="review-card review-card--gate">
              <div className="review-card-meta">
                <span>第 {gateIndex + 1} 关 · {gates[gateIndex].name}</span>
                <span>{repairMode ? '错词修正' : `第 ${itemIndex + 1} / ${roundIds.length} 词`}</span>
              </div>
              <div className="review-progress" aria-label={`本关进度 ${itemIndex + 1}/${roundIds.length}`}>
                <span style={{ width: `${progress}%` }} />
              </div>
              <p className="review-gate-method">{gates[gateIndex].method}</p>
              {gateIndex === 0 && question.phonetic && (
                <p className="review-phonetic">/{question.phonetic}/</p>
              )}
              <p className="review-prompt">{task.prompt}</p>
              <p className="review-task-detail">{task.detail}</p>
              {(question.source_book_title || question.source_chapter_title) && (
                <p className="review-source">
                  来自 {question.source_book_title} · {question.source_chapter_title}
                </p>
              )}
              <form onSubmit={submitAnswer}>
                {task.mode === 'choice' ? (
                  <div className="review-options" role="group" aria-label="选择答案">
                    {task.options.map((option) => (
                      <button
                        className={answer === option ? 'selected' : ''}
                        type="button"
                        disabled={Boolean(feedback)}
                        key={option}
                        onClick={() => setAnswer(option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <label className="review-input">
                    {task.answerLabel}
                    <input
                      autoComplete="off"
                      disabled={Boolean(feedback)}
                      value={answer}
                      onChange={(event) => setAnswer(event.target.value)}
                    />
                  </label>
                )}
                {!feedback && (
                  <button className="review-submit" type="submit" disabled={!answer.trim()}>
                    确认答案
                  </button>
                )}
              </form>
              {feedback && (
                <div
                  className={`review-result review-result--${feedback.correct ? 'correct' : 'wrong'}`}
                  role="status"
                >
                  <strong>{feedback.correct ? '回答正确' : '加入修正'}</strong>
                  <p>{feedback.text}</p>
                  <button type="button" onClick={nextTask}>
                    {itemIndex + 1 === roundIds.length ? '查看本关结果' : '下一个词 →'}
                  </button>
                </div>
              )}
            </section>
          ) : null}
        </>
      )}

      {completion && (
        <section className="review-finished">
          <span aria-hidden="true">✓</span>
          <p className="eyebrow">Journey Complete</p>
          <h2>五关全部完成</h2>
          <p>
            本轮掌握 {completion.completed_count} 个生词，
            {completion.repaired_count > 0
              ? `其中 ${completion.repaired_count} 个经过错词修正。`
              : '全部一次通过。'}
          </p>
          <p>下一次复习安排在 {formatReviewTime(completion.next_review_at)}。</p>
          <div>
            <button type="button" onClick={onBack}>返回书架</button>
            <button type="button" onClick={onVocabulary}>查看生词库</button>
          </div>
        </section>
      )}
    </main>
  )
}

function GateOutcomeView({
  gate,
  outcome,
  repairMode,
  submitting,
  finalGate,
  onContinue,
}: {
  gate: GateDefinition
  outcome: GateOutcome
  repairMode: boolean
  submitting: boolean
  finalGate: boolean
  onContinue: () => void
}) {
  const needsRepair = outcome.missedIds.length > 0
  const passed = outcome.score >= 80
  const title = needsRepair
    ? passed ? '本关通过，先修正错词' : '本关需要加强'
    : repairMode ? '修正完成' : '本关一次通过'
  const action = needsRepair
    ? `修正 ${outcome.missedIds.length} 个词`
    : finalGate ? '完成训练' : '进入下一关'

  return (
    <section className="review-gate-outcome">
      <span className="review-gate-score">{outcome.score}%</span>
      <p className="eyebrow">{gate.shortName} · Gate Complete</p>
      <h2>{title}</h2>
      <p>
        {needsRepair
          ? `答错的词只需单独修正，不用重新完成整关。通关标准为 80%。`
          : '这一关已经完成，可以继续向主动回想前进。'}
      </p>
      <button type="button" disabled={submitting} onClick={onContinue}>
        {submitting ? '正在保存…' : action}
      </button>
    </section>
  )
}

function buildGateTask(
  question: ReviewQuestion,
  gateIndex: number,
  questions: ReviewQuestion[],
): GateTask {
  const lemma = question.lemma || 'word'
  const meanings = question.meanings || []
  const meaning = meanings[0] || '暂未收录释义'
  const context = question.context || question.prompt
  if (gateIndex === 0) {
    return {
      mode: 'choice',
      prompt: lemma,
      detail: `${meaning} · ${context}`,
      options: ['认识这个词', '需要再看'],
      correctAnswer: '认识这个词',
      answerLabel: '',
    }
  }
  if (gateIndex === 1) {
    return {
      mode: 'choice',
      prompt: `“${lemma}”最符合哪个释义？`,
      detail: '先回想，再选择。',
      options: makeOptions(meaning, questions.flatMap((item) => item.meanings || []), '还不确定'),
      correctAnswer: meaning,
      answerLabel: '',
    }
  }
  if (gateIndex === 2) {
    return {
      mode: 'choice',
      prompt: maskWord(context, lemma),
      detail: '选择最适合放回原句的单词。',
      options: makeOptions(lemma, questions.map((item) => item.lemma).filter(Boolean), '想不起来'),
      correctAnswer: lemma,
      answerLabel: '',
    }
  }
  if (gateIndex === 3) {
    return {
      mode: 'input',
      prompt: maskWord(context, lemma),
      detail: `提示：${lemma[0]?.toUpperCase() || ''} 开头，共 ${lemma.length} 个字母`,
      options: [],
      correctAnswer: lemma,
      answerLabel: '填写缺少的英文单词',
    }
  }
  return {
    mode: 'input',
    prompt: `“${meaning}”用英语怎么表达？`,
    detail: '不提供选项，主动回想并写出完整单词。',
    options: [],
    correctAnswer: lemma,
    answerLabel: '填写对应的英文单词',
  }
}

function makeOptions(correct: string, pool: string[], fallback: string): string[] {
  const distractors = [...new Set(pool.filter((item) => item && item !== correct))].slice(0, 3)
  if (distractors.length === 0) distractors.push(fallback)
  return deterministicShuffle([correct, ...distractors], correct)
}

function deterministicShuffle(values: string[], seed: string): string[] {
  const result = [...values]
  let state = [...seed].reduce((sum, character) => sum + character.charCodeAt(0), 0)
  for (let index = result.length - 1; index > 0; index -= 1) {
    state = (state * 9301 + 49297) % 233280
    const target = Math.floor((state / 233280) * (index + 1))
    ;[result[index], result[target]] = [result[target], result[index]]
  }
  return result
}

function maskWord(context: string, lemma: string): string {
  const pattern = new RegExp(`\\b${escapeRegExp(lemma)}\\b`, 'i')
  return pattern.test(context)
    ? context.replace(pattern, '_____')
    : `Complete the word: _____ (${lemma.length} letters)`
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeAnswer(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}

function addUnique(values: string[], value: string): string[] {
  return values.includes(value) ? values : [...values, value]
}

function formatReviewTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
