'use client'

import { useState } from 'react'
import Button from '@/components/ui/Button'

const FEEDBACK_MAX_LENGTH = 1000

interface RevisionFeedbackFormProps {
  onSubmit: (feedback: string) => void
  isSubmitting: boolean
  disabled: boolean
  error?: string | null
  inputId: string
  placeholder: string
  label?: string
  submitLabel?: string
}

export default function RevisionFeedbackForm({
  onSubmit,
  isSubmitting,
  disabled,
  error,
  inputId,
  placeholder,
  label = '修正を依頼する',
  submitLabel = 'この内容で修正を依頼する',
}: RevisionFeedbackFormProps) {
  const [feedback, setFeedback] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!feedback.trim()) return
    onSubmit(feedback.trim())
  }

  const isDisabled = isSubmitting || disabled

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-sm font-medium text-text-secondary">
          {label}
        </label>
        <textarea
          id={inputId}
          rows={3}
          maxLength={FEEDBACK_MAX_LENGTH}
          placeholder={placeholder}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={isDisabled}
          className="bg-background border border-border rounded-lg px-3 py-2 text-text-primary text-sm w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
        />
        <p className="text-xs text-text-secondary text-right">
          {feedback.length} / {FEEDBACK_MAX_LENGTH}
        </p>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex justify-end">
        <Button
          type="submit"
          variant="secondary"
          isLoading={isSubmitting}
          disabled={!feedback.trim() || isDisabled}
        >
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
