import { type ChangeEvent, useEffect, useRef, useState } from 'react'

import { type BookSummary, fetchBooks, importBook } from './api/books'
import ReaderView from './ReaderView'
import ReviewView from './ReviewView'
import VocabularyView from './VocabularyView'

type ServiceStatus = 'checking' | 'ready' | 'offline'
type LibraryStatus = 'loading' | 'ready' | 'error'

interface HealthResponse {
  status: string
  database: string
}

export default function App() {
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>('checking')
  const [libraryStatus, setLibraryStatus] = useState<LibraryStatus>('loading')
  const [books, setBooks] = useState<BookSummary[]>([])
  const [isImporting, setIsImporting] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [readingBookId, setReadingBookId] = useState<string | null>(null)
  const [view, setView] = useState<'library' | 'vocabulary' | 'review'>('library')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/v1/health', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Service unavailable')
        return response.json() as Promise<HealthResponse>
      })
      .then((health) => {
        setServiceStatus(
          health.status === 'ok' && health.database === 'ok' ? 'ready' : 'offline',
        )
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setServiceStatus('offline')
      })

    fetchBooks()
      .then((loadedBooks) => {
        setBooks(loadedBooks)
        setLibraryStatus('ready')
      })
      .catch(() => setLibraryStatus('error'))

    return () => controller.abort()
  }, [])

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    const extension = file.name.toLowerCase().split('.').pop()
    if (extension !== 'txt' && extension !== 'epub') {
      setNotice('请选择 TXT 或 EPUB 格式的英文读物')
      return
    }

    setIsImporting(true)
    setNotice(null)
    try {
      const importedBook = await importBook(file)
      setBooks((current) => [importedBook, ...current])
      setLibraryStatus('ready')
      setNotice(`《${importedBook.title}》导入成功`)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '导入失败，请稍后重试')
    } finally {
      setIsImporting(false)
    }
  }

  const serviceText = {
    checking: '正在连接',
    ready: '本地服务已就绪',
    offline: '本地服务未启动',
  }[serviceStatus]

  if (readingBookId) {
    return (
      <ReaderView
        bookId={readingBookId}
        onClose={() => setReadingBookId(null)}
        onProgressChange={(bookId, percentage, chapterId) => {
          setBooks((current) =>
            current.map((book) =>
              book.id === bookId
                ? { ...book, progress_percentage: percentage, current_chapter_id: chapterId }
                : book,
            ),
          )
        }}
      />
    )
  }

  if (view === 'vocabulary') {
    return <VocabularyView onBack={() => setView('library')} />
  }

  if (view === 'review') {
    return (
      <ReviewView
        onBack={() => setView('library')}
        onVocabulary={() => setView('vocabulary')}
      />
    )
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">RM</span>
          <span>ReadMaster</span>
        </div>
        <nav aria-label="主要导航">
          <a className="active" href="#library">
            书架
          </a>
          <button type="button" onClick={() => setView('vocabulary')}>生词</button>
          <button type="button" onClick={() => setView('review')}>训练</button>
        </nav>
        <div className={`service-status service-status--${serviceStatus}`} role="status">
          <span aria-hidden="true" />
          {serviceText}
        </div>
      </header>

      <section className="library-header" id="library">
        <div>
          <p className="eyebrow">Your Reading Library</p>
          <h1>我的书架</h1>
          <p>把英文读物放进来，从真实语境开始积累理解。</p>
        </div>
        <button
          className="import-button"
          type="button"
          disabled={isImporting || serviceStatus === 'offline'}
          onClick={() => fileInputRef.current?.click()}
        >
          {isImporting ? '正在导入…' : '导入书籍'}
        </button>
        <input
          ref={fileInputRef}
          className="visually-hidden"
          type="file"
          accept=".txt,.epub,text/plain,application/epub+zip"
          aria-label="选择 TXT 或 EPUB 文件"
          onChange={handleFileChange}
        />
      </section>

      {notice && <div className="notice">{notice}</div>}

      <section className="library-content" aria-live="polite">
        {libraryStatus === 'loading' && <LibraryMessage title="正在整理书架…" />}
        {libraryStatus === 'error' && (
          <LibraryMessage title="暂时无法读取书架" detail="请确认本地后端服务已经启动。" />
        )}
        {libraryStatus === 'ready' && books.length === 0 && (
          <LibraryMessage
            title="书架还是空的"
            detail="导入第一本 TXT 或 EPUB 英文读物，ReadMaster 会自动整理章节和段落。"
            action={
              <button type="button" onClick={() => fileInputRef.current?.click()}>
                选择一本书
              </button>
            }
          />
        )}
        {libraryStatus === 'ready' && books.length > 0 && (
          <div className="book-grid">
            {books.map((book, index) => (
              <article className="book-card" key={book.id}>
                <div className={`book-cover book-cover--${(index % 3) + 1}`} aria-hidden="true">
                  <span>READ</span>
                  <strong>{getInitials(book.title)}</strong>
                </div>
                <div className="book-info">
                  <p className="book-format">{book.format} · {book.chapter_count} 章</p>
                  <h2>{book.title}</h2>
                  <p className="book-author">{book.author || '作者未知'}</p>
                  <div className="book-meta">
                    <span>{book.source_filename}</span>
                    <time dateTime={book.created_at}>{formatDate(book.created_at)}</time>
                  </div>
                  <div className="book-progress" aria-label={`阅读进度 ${Math.round(book.progress_percentage)}%`}>
                    <span style={{ width: `${book.progress_percentage}%` }} />
                  </div>
                  <button type="button" onClick={() => setReadingBookId(book.id)}>
                    {book.progress_percentage > 0 ? '继续阅读' : '开始阅读'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

function LibraryMessage({
  title,
  detail,
  action,
}: {
  title: string
  detail?: string
  action?: React.ReactNode
}) {
  return (
    <div className="library-message">
      <span aria-hidden="true">Aa</span>
      <h2>{title}</h2>
      {detail && <p>{detail}</p>}
      {action}
    </div>
  )
}

function getInitials(title: string): string {
  const words = title.trim().split(/\s+/).filter(Boolean)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return words
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}
