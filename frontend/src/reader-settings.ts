export type ReaderTheme = 'paper' | 'night'

export interface ReaderSettings {
  fontSize: number
  lineHeight: number
  contentWidth: number
  theme: ReaderTheme
  showChinese: boolean
}

export const defaultReaderSettings: ReaderSettings = {
  fontSize: 20,
  lineHeight: 1.85,
  contentWidth: 760,
  theme: 'paper',
  showChinese: true,
}

const storageKey = 'readmaster.reader-settings'

export function loadReaderSettings(): ReaderSettings {
  try {
    const stored = localStorage.getItem(storageKey)
    if (!stored) return defaultReaderSettings
    const parsed = JSON.parse(stored) as Partial<ReaderSettings>
    return {
      fontSize: clampNumber(parsed.fontSize, 16, 30, defaultReaderSettings.fontSize),
      lineHeight: clampNumber(parsed.lineHeight, 1.4, 2.4, defaultReaderSettings.lineHeight),
      contentWidth: clampNumber(parsed.contentWidth, 600, 1000, defaultReaderSettings.contentWidth),
      theme: parsed.theme === 'night' ? 'night' : 'paper',
      showChinese: parsed.showChinese !== false,
    }
  } catch {
    return defaultReaderSettings
  }
}

export function storeReaderSettings(settings: ReaderSettings): void {
  localStorage.setItem(storageKey, JSON.stringify(settings))
}

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, value))
}
