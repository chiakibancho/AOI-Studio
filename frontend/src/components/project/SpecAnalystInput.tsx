'use client'

import { useState, useEffect } from 'react'
import Button from '@/components/ui/Button'

const MAX_LENGTH = 4000

interface SpecAnalystInputProps {
  initialValue?: string
  onSubmit: (rawInput: string) => void
  isSubmitting: boolean
  error?: string | null
  onManualEntry: () => void
}

export default function SpecAnalystInput({
  initialValue = '',
  onSubmit,
  isSubmitting,
  error,
  onManualEntry,
}: SpecAnalystInputProps) {
  const [rawInput, setRawInput] = useState(initialValue)

  useEffect(() => {
    setRawInput(initialValue)
  }, [initialValue])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!rawInput.trim()) return
    onSubmit(rawInput.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          どんな動画を作りたいか、自由に書いてください
        </label>
        <textarea
          rows={6}
          maxLength={MAX_LENGTH}
          placeholder="例: 20代向けの採用動画を90秒くらいで、社員インタビュー中心の親しみやすい雰囲気で作りたい"
          value={rawInput}
          onChange={(e) => setRawInput(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-text-primary text-sm w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <p className="text-xs text-text-secondary text-right">
          {rawInput.length} / {MAX_LENGTH}
        </p>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onManualEntry}
          className="text-sm text-text-secondary hover:text-accent transition-colors duration-200"
        >
          手動で入力する
        </button>
        <Button
          type="submit"
          variant="primary"
          isLoading={isSubmitting}
          disabled={!rawInput.trim()}
        >
          AIに分析してもらう
        </Button>
      </div>
    </form>
  )
}
