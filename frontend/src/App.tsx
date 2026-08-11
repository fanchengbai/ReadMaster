import { useEffect, useState } from 'react'

type ServiceStatus = 'checking' | 'ready' | 'offline'

interface HealthResponse {
  status: string
  version: string
  database: string
}

export default function App() {
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>('checking')

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

    return () => controller.abort()
  }, [])

  const statusText = {
    checking: '正在连接本地服务…',
    ready: '本地服务已就绪',
    offline: '本地服务尚未启动',
  }[serviceStatus]

  return (
    <main className="shell">
      <header className="brand">
        <span className="brand-mark">RM</span>
        <span>ReadMaster</span>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <p className="eyebrow">Personal English Reading Intelligence System</p>
        <h1 id="hero-title">从真实阅读开始，建立自己的英文理解能力。</h1>
        <p className="summary">
          导入英文内容，在语境中发现词汇、积累理解，并让每一次阅读成为下一次进步的基础。
        </p>
        <div className={`service-status service-status--${serviceStatus}`} role="status">
          <span aria-hidden="true" />
          {statusText}
        </div>
      </section>

      <section className="roadmap" aria-label="第一版能力">
        <article>
          <span>01</span>
          <h2>导入文本</h2>
          <p>从 TXT 英文读物开始，自动整理章节与段落。</p>
        </article>
        <article>
          <span>02</span>
          <h2>沉浸阅读</h2>
          <p>保持简洁的正文体验，在需要时点击单词。</p>
        </article>
        <article>
          <span>03</span>
          <h2>积累生词</h2>
          <p>保存释义、来源与语境，让词汇回到阅读中。</p>
        </article>
      </section>
    </main>
  )
}

