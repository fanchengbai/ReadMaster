import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react'

import {
  type BookDetail,
  type ChapterContent,
  fetchBook,
  fetchChapter,
  fetchProgress,
  saveProgress,
} from './api/books'
import {
  type ReaderSettings,
  loadReaderSettings,
  storeReaderSettings,
} from './reader-settings'

interface ReaderViewProps {
  bookId: string
  onClose: () => void
  onProgressChange: (bookId: string, percentage: number, chapterId: string) => void
}

export default function ReaderView({ bookId, onClose, onProgressChange }: ReaderViewProps) {
  const [book, setBook] = useState<BookDetail | null>(null)
  const [chapter, setChapter] = useState<ChapterContent | null>(null)
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null)
  const [activeParagraphId, setActiveParagraphId] = useState<string | null>(null)
  const [settings, setSettings] = useState<ReaderSettings>(loadReaderSettings)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [contentsOpen, setContentsOpen] = useState(true)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const articleRef = useRef<HTMLElement>(null)
  const lastSavedRef = useRef('')
  const resumeParagraphRef = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchBook(bookId), fetchProgress(bookId)])
      .then(([loadedBook, progress]) => {
        if (cancelled) return
        setBook(loadedBook)
        resumeParagraphRef.current = progress.paragraph_id
        setActiveChapterId(progress.chapter_id || loadedBook.chapters[0]?.id || null)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setErrorMessage(error instanceof Error ? error.message : '无法打开这本书')
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [bookId])

  useEffect(() => {
    if (!activeChapterId) return
    let cancelled = false
    fetchChapter(activeChapterId)
      .then((loadedChapter) => {
        if (cancelled) return
        const resumeParagraphId = loadedChapter.paragraphs.some(
          (paragraph) => paragraph.id === resumeParagraphRef.current,
        )
          ? resumeParagraphRef.current
          : loadedChapter.paragraphs[0]?.id ?? null
        resumeParagraphRef.current = null
        setChapter(loadedChapter)
        setActiveParagraphId(resumeParagraphId)
        setStatus('ready')
        window.requestAnimationFrame(() => {
          const scrollTarget = resumeParagraphId
            ? document.getElementById(`paragraph-${resumeParagraphId}`)
            : articleRef.current
          if (typeof scrollTarget?.scrollIntoView === 'function') {
            scrollTarget.scrollIntoView({ block: resumeParagraphId ? 'center' : 'start' })
          }
        })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setErrorMessage(error instanceof Error ? error.message : '无法读取章节')
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [activeChapterId])

  useEffect(() => {
    storeReaderSettings(settings)
  }, [settings])

  useEffect(() => {
    if (!chapter || status !== 'ready' || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]
        const paragraphId = (visible?.target as HTMLElement | undefined)?.dataset.paragraphId
        if (paragraphId) setActiveParagraphId(paragraphId)
      },
      { rootMargin: '-18% 0px -45% 0px', threshold: [0.15, 0.5, 0.85] },
    )
    const paragraphs = articleRef.current?.querySelectorAll<HTMLElement>('[data-paragraph-id]')
    paragraphs?.forEach((paragraph) => observer.observe(paragraph))
    return () => observer.disconnect()
  }, [chapter, status])

  const activeIndex = useMemo(
    () => book?.chapters.findIndex((item) => item.id === activeChapterId) ?? -1,
    [book, activeChapterId],
  )
  const paragraphIndex =
    chapter?.paragraphs.findIndex((paragraph) => paragraph.id === activeParagraphId) ?? -1
  const paragraphFraction =
    chapter && chapter.paragraphs.length > 0 && paragraphIndex >= 0
      ? (paragraphIndex + 1) / chapter.paragraphs.length
      : 0
  const percentage =
    book && activeIndex >= 0
      ? ((activeIndex + paragraphFraction) / book.chapters.length) * 100
      : 0

  useEffect(() => {
    if (!book || !chapter || !activeParagraphId || status !== 'ready') return
    const key = `${book.id}:${chapter.id}:${activeParagraphId}:${percentage.toFixed(2)}`
    if (lastSavedRef.current === key) return
    lastSavedRef.current = key
    const timer = window.setTimeout(() => {
      saveProgress(book.id, {
        chapter_id: chapter.id,
        paragraph_id: activeParagraphId,
        percentage,
      })
        .then(() => onProgressChange(book.id, percentage, chapter.id))
        .catch(() => {
          lastSavedRef.current = ''
        })
    }, 500)
    return () => window.clearTimeout(timer)
  }, [activeParagraphId, book, chapter, onProgressChange, percentage, status])

  function changeChapter(chapterId: string) {
    if (chapterId === activeChapterId) return
    setStatus('loading')
    setActiveParagraphId(null)
    setActiveChapterId(chapterId)
    if (window.innerWidth < 900) setContentsOpen(false)
  }

  function updateSettings(patch: Partial<ReaderSettings>) {
    setSettings((current) => ({ ...current, ...patch }))
  }

  const readerStyle = {
    '--reader-font-size': `${settings.fontSize}px`,
    '--reader-line-height': settings.lineHeight,
    '--reader-width': `${settings.contentWidth}px`,
  } as CSSProperties

  return (
    <div className={`reader-screen reader-screen--${settings.theme}`} style={readerStyle}>
      <header className="reader-topbar">
        <button className="reader-back" type="button" onClick={onClose}>
          <span aria-hidden="true">←</span> 书架
        </button>
        <div className="reader-book-title">
          <strong>{book?.title || '正在打开…'}</strong>
          <span>{chapter?.title || '正在读取章节'}</span>
        </div>
        <div className="reader-actions">
          <button type="button" onClick={() => setContentsOpen((open) => !open)}>
            目录
          </button>
          <button type="button" onClick={() => setSettingsOpen((open) => !open)}>
            阅读设置
          </button>
        </div>
      </header>

      <div className="reader-progress" aria-label={`阅读进度 ${Math.round(percentage)}%`}>
        <span style={{ width: `${percentage}%` }} />
      </div>

      {settingsOpen && (
        <aside className="reader-settings" aria-label="阅读设置">
          <label>
            字号
            <input
              type="range"
              min="16"
              max="30"
              value={settings.fontSize}
              onChange={(event) => updateSettings({ fontSize: Number(event.target.value) })}
            />
            <output>{settings.fontSize}px</output>
          </label>
          <label>
            行距
            <input
              type="range"
              min="1.4"
              max="2.4"
              step="0.1"
              value={settings.lineHeight}
              onChange={(event) => updateSettings({ lineHeight: Number(event.target.value) })}
            />
            <output>{settings.lineHeight.toFixed(1)}</output>
          </label>
          <label>
            宽度
            <input
              type="range"
              min="600"
              max="1000"
              step="20"
              value={settings.contentWidth}
              onChange={(event) => updateSettings({ contentWidth: Number(event.target.value) })}
            />
            <output>{settings.contentWidth}px</output>
          </label>
          <div className="theme-options" aria-label="阅读主题">
            <button
              className={settings.theme === 'paper' ? 'active' : ''}
              type="button"
              onClick={() => updateSettings({ theme: 'paper' })}
            >
              纸张
            </button>
            <button
              className={settings.theme === 'night' ? 'active' : ''}
              type="button"
              onClick={() => updateSettings({ theme: 'night' })}
            >
              夜间
            </button>
          </div>
        </aside>
      )}

      <div className="reader-layout">
        {contentsOpen && (
          <aside className="chapter-sidebar" aria-label="章节目录">
            <p>CONTENTS</p>
            <ol>
              {book?.chapters.map((item) => (
                <li key={item.id}>
                  <button
                    className={item.id === activeChapterId ? 'active' : ''}
                    type="button"
                    onClick={() => changeChapter(item.id)}
                  >
                    <span>{String(item.order_index + 1).padStart(2, '0')}</span>
                    {item.title}
                  </button>
                </li>
              ))}
            </ol>
          </aside>
        )}

        <main className="reader-main">
          {status === 'loading' && <div className="reader-message">正在打开章节…</div>}
          {status === 'error' && <div className="reader-message">{errorMessage}</div>}
          {status === 'ready' && chapter && (
            <article ref={articleRef} className="reading-article">
              <div className="chapter-kicker">
                Chapter {String(chapter.order_index + 1).padStart(2, '0')}
              </div>
              <h1>{chapter.title}</h1>
              {chapter.paragraphs.map((paragraph) => (
                <p
                  id={`paragraph-${paragraph.id}`}
                  key={paragraph.id}
                  data-paragraph-id={paragraph.id}
                >
                  {paragraph.content}
                </p>
              ))}
              <nav className="chapter-navigation" aria-label="章节切换">
                <button
                  type="button"
                  disabled={!book || activeIndex <= 0}
                  onClick={() => book && changeChapter(book.chapters[activeIndex - 1].id)}
                >
                  ← 上一章
                </button>
                <span>{Math.round(percentage)}%</span>
                <button
                  type="button"
                  disabled={!book || activeIndex < 0 || activeIndex >= book.chapters.length - 1}
                  onClick={() => book && changeChapter(book.chapters[activeIndex + 1].id)}
                >
                  下一章 →
                </button>
              </nav>
            </article>
          )}
        </main>
      </div>
    </div>
  )
}
