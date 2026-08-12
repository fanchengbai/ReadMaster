import type { WordSelection } from './api/vocabulary'

interface ClickableParagraphProps {
  bookId: string
  chapterId: string
  paragraphId: string
  content: string
  onWordClick: (selection: WordSelection) => void
}

const wordPattern = /[A-Za-z]+(?:['’-][A-Za-z]+)*/g

export default function ClickableParagraph({
  bookId,
  chapterId,
  paragraphId,
  content,
  onWordClick,
}: ClickableParagraphProps) {
  const pieces: React.ReactNode[] = []
  let cursor = 0

  for (const match of content.matchAll(wordPattern)) {
    const start = match.index
    const word = match[0]
    if (start > cursor) pieces.push(content.slice(cursor, start))
    pieces.push(
      <button
        className="reader-word"
        type="button"
        key={`${start}-${word}`}
        onClick={() =>
          onWordClick({
            word,
            book_id: bookId,
            chapter_id: chapterId,
            paragraph_id: paragraphId,
            char_start: start,
            char_end: start + word.length,
          })
        }
      >
        {word}
      </button>,
    )
    cursor = start + word.length
  }
  if (cursor < content.length) pieces.push(content.slice(cursor))

  return <>{pieces}</>
}
