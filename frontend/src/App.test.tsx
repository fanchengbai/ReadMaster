import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import App from './App'

afterEach(() => {
  vi.restoreAllMocks()
})

test('shows the product purpose and a ready service state', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ status: 'ok', version: '0.1.0', database: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  render(<App />)

  expect(
    screen.getByRole('heading', { name: '从真实阅读开始，建立自己的英文理解能力。' }),
  ).toBeInTheDocument()
  expect(await screen.findByText('本地服务已就绪')).toBeInTheDocument()
})

