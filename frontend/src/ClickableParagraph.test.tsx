import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import ClickableParagraph from './ClickableParagraph'

afterEach(cleanup)

test('keeps the exact word position when a reader selects a word', () => {
  const onWordClick = vi.fn()

  render(
    <p>
      <ClickableParagraph
        bookId="book-1"
        chapterId="chapter-1"
        paragraphId="paragraph-1"
        content="A curious reader's journey."
        onWordClick={onWordClick}
      />
    </p>,
  )

  fireEvent.click(screen.getByRole('button', { name: 'curious' }))

  expect(onWordClick).toHaveBeenCalledWith({
    word: 'curious',
    book_id: 'book-1',
    chapter_id: 'chapter-1',
    paragraph_id: 'paragraph-1',
    char_start: 2,
    char_end: 9,
  })
  expect(screen.getByRole('button', { name: "reader's" })).toBeInTheDocument()
})
