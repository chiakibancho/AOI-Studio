'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { VideoType, Project } from '@/types'
import { VIDEO_TYPE_LABELS } from '@/types'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
}

const VIDEO_TYPES: VideoType[] = [
  'brand',
  'corporate',
  'recruitment',
  'sns_ad',
  'youtube',
  'short',
  'product_pr',
]

export default function NewProjectModal({ isOpen, onClose }: NewProjectModalProps) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [videoType, setVideoType] = useState<VideoType>('brand')
  const [titleError, setTitleError] = useState('')

  const { mutate, isPending, error } = useMutation({
    mutationFn: async () => {
      const res = await api.post<Project>('/api/v1/projects', {
        title,
        video_type: videoType,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      handleClose()
    },
  })

  function handleClose() {
    setTitle('')
    setVideoType('brand')
    setTitleError('')
    onClose()
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) {
      setTitleError('プロジェクト名を入力してください')
      return
    }
    if (title.trim().length > 100) {
      setTitleError('プロジェクト名は100文字以内で入力してください')
      return
    }
    setTitleError('')
    mutate()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-2xl bg-surface border border-border shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">新規プロジェクト作成</h2>
          <button
            onClick={handleClose}
            className="rounded-lg p-1.5 text-text-secondary hover:text-text-primary hover:bg-border transition-colors"
            aria-label="閉じる"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
          <Input
            label="プロジェクト名"
            placeholder="例: 2024年 会社紹介動画"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            error={titleError}
            autoFocus
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-secondary">
              動画タイプ
            </label>
            <div className="grid grid-cols-2 gap-2">
              {VIDEO_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setVideoType(type)}
                  className={`
                    rounded-lg border px-3 py-2.5 text-sm font-medium text-left transition-all duration-150
                    ${
                      videoType === type
                        ? 'bg-accent/20 border-accent text-accent'
                        : 'bg-background border-border text-text-secondary hover:border-accent/40 hover:text-text-primary'
                    }
                  `}
                >
                  {VIDEO_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              プロジェクトの作成に失敗しました。もう一度お試しください。
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={handleClose}
              disabled={isPending}
            >
              キャンセル
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={isPending}
            >
              作成する
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
