import { useEffect, useState } from 'react'

import {
  type DictionaryEntry,
  type WordSelection,
  lookupWord,
  saveUserWord,
} from './api/vocabulary'

interface WordCardProps {
  selection: WordSelection
  context: string
  onClose: () => void
  onSaved: () => void
}

export default function WordCard({ selection, context, onClose, onSaved }: WordCardProps) {
  const [entry, setEntry] = useState<DictionaryEntry | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    lookupWord(selection.word)
      .then((result) => {
        if (cancelled) return
        setEntry(result)
        setStatus('ready')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setMessage(error instanceof Error ? error.message : '暂时无法查询')
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [selection])

  async function handleSave() {
    setSaving(true)
    setMessage('')
    try {
      await saveUserWord(selection)
      setEntry((current) => (current ? { ...current, saved: true } : current))
      setMessage('已保存到生词库')
      onSaved()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <aside className="word-card" aria-label="词汇卡片">
      <button className="word-card-close" type="button" aria-label="关闭词汇卡片" onClick={onClose}>
        ×
      </button>
      {status === 'loading' && <p className="word-card-state">正在查询…</p>}
      {status === 'error' && <p className="word-card-state">{message}</p>}
      {status === 'ready' && entry && (
        <>
          <p className="word-card-label">Vocabulary</p>
          <h2>{entry.surface_form}</h2>
          <div className="word-lemma">
            <span>{entry.lemma}</span>
            {entry.phonetic && <span>{entry.phonetic}</span>}
          </div>
          {entry.definitions.length > 0 ? (
            <ol className="word-definitions">
              {entry.definitions.map((definition, index) => (
                <li key={`${definition.part_of_speech}-${index}`}>
                  <span>{definition.part_of_speech}</span>
                  <p>{definition.meaning}</p>
                </li>
              ))}
            </ol>
          ) : (
            <div className="word-not-found">
              <strong>基础词典暂未收录</strong>
              <p>仍可保存这个单词及当前语境，后续接入完整词典后会自动补充释义。</p>
            </div>
          )}
          <div className="word-context">
            <span>当前语境</span>
            <p>{highlightContext(selection, context)}</p>
          </div>
          <button
            className="save-word-button"
            type="button"
            disabled={saving || entry.saved}
            onClick={handleSave}
          >
            {entry.saved ? '已在生词库' : saving ? '正在保存…' : '加入生词库'}
          </button>
          {message && <p className="word-card-message">{message}</p>}
        </>
      )}
    </aside>
  )
}

function highlightContext(selection: WordSelection, text: string) {
  return (
    <>
      {text.slice(0, selection.char_start)}
      <mark>{text.slice(selection.char_start, selection.char_end)}</mark>
      {text.slice(selection.char_end)}
    </>
  )
}
