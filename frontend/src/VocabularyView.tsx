import { useEffect, useState } from 'react'

import {
  type Familiarity,
  type UserWord,
  fetchUserWords,
  removeUserWord,
  updateUserWord,
} from './api/vocabulary'

interface VocabularyViewProps {
  onBack: () => void
}

const statusLabels: Record<Familiarity, string> = {
  new: '新加入',
  learning: '学习中',
  familiar: '基本熟悉',
  mastered: '已掌握',
}

export default function VocabularyView({ onBack }: VocabularyViewProps) {
  const [words, setWords] = useState<UserWord[]>([])
  const [filter, setFilter] = useState<Familiarity | 'all'>('all')
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    fetchUserWords(filter === 'all' ? undefined : filter)
      .then((items) => {
        if (cancelled) return
        setWords(items)
        setStatus('ready')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setMessage(error instanceof Error ? error.message : '无法读取生词库')
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [filter])

  async function changeFamiliarity(word: UserWord, familiarity: Familiarity) {
    try {
      const updated = await updateUserWord(word.id, { familiarity })
      if (filter !== 'all' && filter !== familiarity) {
        setWords((current) => current.filter((item) => item.id !== word.id))
      } else {
        setWords((current) => current.map((item) => (item.id === word.id ? updated : item)))
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '更新失败')
    }
  }

  async function deleteWord(word: UserWord) {
    if (!window.confirm(`确定从生词库移除“${word.lemma}”吗？`)) return
    try {
      await removeUserWord(word.id)
      setWords((current) => current.filter((item) => item.id !== word.id))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '删除失败')
    }
  }

  return (
    <main className="vocabulary-screen">
      <header className="vocabulary-topbar">
        <button type="button" onClick={onBack}>← 返回书架</button>
        <strong>ReadMaster</strong>
      </header>
      <section className="vocabulary-header">
        <p className="eyebrow">Personal Vocabulary</p>
        <h1>我的生词</h1>
        <p>让每个单词保留第一次遇见它的语境。</p>
      </section>
      <nav className="vocabulary-filters" aria-label="生词状态筛选">
        <button className={filter === 'all' ? 'active' : ''} type="button" onClick={() => setFilter('all')}>
          全部
        </button>
        {(Object.keys(statusLabels) as Familiarity[]).map((value) => (
          <button
            className={filter === value ? 'active' : ''}
            type="button"
            key={value}
            onClick={() => setFilter(value)}
          >
            {statusLabels[value]}
          </button>
        ))}
      </nav>
      {message && <div className="notice">{message}</div>}
      <section className="vocabulary-list" aria-live="polite">
        {status === 'loading' && <div className="vocabulary-empty">正在整理生词…</div>}
        {status === 'error' && <div className="vocabulary-empty">{message}</div>}
        {status === 'ready' && words.length === 0 && (
          <div className="vocabulary-empty">还没有符合条件的生词。阅读时点击单词即可开始积累。</div>
        )}
        {status === 'ready' && words.map((word) => (
          <article className="vocabulary-item" key={word.id}>
            <div className="vocabulary-word">
              <h2>{word.lemma}</h2>
              {word.phonetic && <span>{word.phonetic}</span>}
              <small>遇见 {word.encounter_count} 次</small>
            </div>
            <div className="vocabulary-detail">
              {word.definitions.length > 0 ? (
                word.definitions.map((definition, index) => (
                  <p className="vocabulary-definition" key={`${definition.part_of_speech}-${index}`}>
                    <span>{definition.part_of_speech}</span> {definition.meaning}
                  </p>
                ))
              ) : (
                <p className="vocabulary-definition muted">基础词典暂未收录释义</p>
              )}
              {word.latest_occurrence && (
                <blockquote>
                  “{word.latest_occurrence.context}”
                  <cite>
                    {word.latest_occurrence.source_book_title} · {word.latest_occurrence.source_chapter_title}
                  </cite>
                </blockquote>
              )}
            </div>
            <div className="vocabulary-actions">
              <label>
                掌握状态
                <select
                  value={word.familiarity}
                  onChange={(event) => changeFamiliarity(word, event.target.value as Familiarity)}
                >
                  {(Object.keys(statusLabels) as Familiarity[]).map((value) => (
                    <option value={value} key={value}>{statusLabels[value]}</option>
                  ))}
                </select>
              </label>
              <button type="button" onClick={() => deleteWord(word)}>移除</button>
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
