'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import type { VideoSpec, SpecFormFields } from '@/types'
import { MOOD_OPTIONS } from '@/types'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'

interface VideoSpecFormProps {
  projectId: string
  initialSpec?: SpecFormFields | null
  onSaved: (spec: VideoSpec) => void
}

interface FormValues {
  duration_sec: string
  target_audience: string
  message: string
  mood: string
  style_notes: string
  reference_urls: string[]
}

interface FormErrors {
  duration_sec?: string
  target_audience?: string
  message?: string
  mood?: string
}

export default function VideoSpecForm({ projectId, initialSpec, onSaved }: VideoSpecFormProps) {
  const [values, setValues] = useState<FormValues>({
    duration_sec: initialSpec ? String(initialSpec.duration_sec) : '',
    target_audience: initialSpec?.target_audience ?? '',
    message: initialSpec?.message ?? '',
    mood: initialSpec?.mood ?? '',
    style_notes: initialSpec?.style_notes ?? '',
    reference_urls: initialSpec?.reference_urls.length ? initialSpec.reference_urls : [''],
  })
  const [errors, setErrors] = useState<FormErrors>({})

  const mutation = useMutation<VideoSpec, Error, FormValues>({
    mutationFn: async (vals) => {
      const payload = {
        duration_sec: Number(vals.duration_sec),
        target_audience: vals.target_audience,
        message: vals.message,
        mood: vals.mood,
        style_notes: vals.style_notes || null,
        reference_urls: vals.reference_urls.filter((u) => u.trim() !== ''),
      }
      const res = await api.put<VideoSpec>(`/api/v1/projects/${projectId}/spec`, payload)
      return res.data
    },
    onSuccess: (data) => {
      onSaved(data)
    },
  })

  function validate(): boolean {
    const newErrors: FormErrors = {}
    const dur = Number(values.duration_sec)
    if (!values.duration_sec || isNaN(dur) || dur < 5 || dur > 3600) {
      newErrors.duration_sec = '5〜3600秒の範囲で入力してください'
    }
    if (!values.target_audience.trim()) {
      newErrors.target_audience = 'ターゲット層を入力してください'
    }
    if (!values.message.trim()) {
      newErrors.message = '伝えたいメッセージを入力してください'
    }
    if (!values.mood) {
      newErrors.mood = '雰囲気・トーンを選択してください'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    mutation.mutate(values)
  }

  function handleUrlChange(index: number, value: string) {
    setValues((prev) => {
      const urls = [...prev.reference_urls]
      urls[index] = value
      return { ...prev, reference_urls: urls }
    })
  }

  function addUrl() {
    if (values.reference_urls.length >= 5) return
    setValues((prev) => ({ ...prev, reference_urls: [...prev.reference_urls, ''] }))
  }

  function removeUrl(index: number) {
    setValues((prev) => {
      const urls = prev.reference_urls.filter((_, i) => i !== index)
      return { ...prev, reference_urls: urls.length === 0 ? [''] : urls }
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      {/* duration_sec */}
      <Input
        label="目標尺（秒）"
        type="number"
        min={5}
        max={3600}
        placeholder="例: 90"
        value={values.duration_sec}
        onChange={(e) => setValues((prev) => ({ ...prev, duration_sec: e.target.value }))}
        error={errors.duration_sec}
      />

      {/* target_audience */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          ターゲット層
        </label>
        <textarea
          rows={3}
          placeholder="例: 20〜30代の採用担当者、BtoBの意思決定者"
          value={values.target_audience}
          onChange={(e) => setValues((prev) => ({ ...prev, target_audience: e.target.value }))}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-text-primary text-sm w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent"
        />
        {errors.target_audience && (
          <p className="text-xs text-red-400">{errors.target_audience}</p>
        )}
      </div>

      {/* message */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          伝えたいメッセージ
        </label>
        <textarea
          rows={4}
          placeholder="例: 当社の技術力と働きやすい職場環境を伝え、エンジニアの採用につなげたい"
          value={values.message}
          onChange={(e) => setValues((prev) => ({ ...prev, message: e.target.value }))}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-text-primary text-sm w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent"
        />
        {errors.message && (
          <p className="text-xs text-red-400">{errors.message}</p>
        )}
      </div>

      {/* mood */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          雰囲気・トーン
        </label>
        <div className="flex flex-wrap gap-2">
          {MOOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setValues((prev) => ({ ...prev, mood: opt.value }))}
              className={`
                px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200
                ${values.mood === opt.value
                  ? 'bg-accent border-accent text-white'
                  : 'bg-surface border-border text-text-secondary hover:border-accent/50 hover:text-text-primary'
                }
              `}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {errors.mood && (
          <p className="text-xs text-red-400">{errors.mood}</p>
        )}
      </div>

      {/* style_notes */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          スタイル補足（任意）
        </label>
        <textarea
          rows={3}
          placeholder="例: 社員インタビューを中心に、オフィスや製品の映像を交える"
          value={values.style_notes}
          onChange={(e) => setValues((prev) => ({ ...prev, style_notes: e.target.value }))}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-text-primary text-sm w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      {/* reference_urls */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-secondary">
          参考URL（任意）
        </label>
        <div className="flex flex-col gap-2">
          {values.reference_urls.map((url, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => handleUrlChange(index, e.target.value)}
                className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-text-secondary"
              />
              {values.reference_urls.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeUrl(index)}
                  className="text-text-secondary hover:text-red-400 transition-colors duration-200 p-1"
                  aria-label="URLを削除"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          ))}
          {values.reference_urls.length < 5 && (
            <button
              type="button"
              onClick={addUrl}
              className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-accent transition-colors duration-200 w-fit"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              URLを追加
            </button>
          )}
        </div>
      </div>

      {/* API error */}
      {mutation.isError && (
        <p className="text-sm text-red-400">
          保存に失敗しました。もう一度お試しください。
        </p>
      )}

      <div className="flex justify-end">
        <Button
          type="submit"
          variant="primary"
          isLoading={mutation.isPending}
        >
          保存する
        </Button>
      </div>
    </form>
  )
}
