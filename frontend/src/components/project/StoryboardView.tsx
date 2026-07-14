'use client'

import type { Storyboard, StoryboardScene, Structure } from '@/types'
import Button from '@/components/ui/Button'
import RevisionFeedbackForm from '@/components/project/RevisionFeedbackForm'

interface StoryboardViewProps {
  projectId: string
  storyboard: Storyboard
  structure: Structure
  onRegenerate: () => void
  onApprove: () => void
  onRevise: (feedback: string) => void
  isRegenerating: boolean
  isApproving: boolean
  isRevising: boolean
  reviseError?: string | null
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function StoryboardSceneCard({
  scene,
  title,
}: {
  scene: StoryboardScene
  title: string
}) {
  return (
    <div className="flex-shrink-0 w-72 rounded-xl border border-border bg-surface p-5 flex flex-col gap-3">
      {/* Scene header */}
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center">
          <span className="text-xs font-bold text-white">{scene.scene_number}</span>
        </div>
        <div className="flex-1 min-w-0">
          <span className="font-semibold text-text-primary text-sm">{title}</span>
          <p className="text-xs text-text-secondary mt-0.5">
            {formatTime(scene.time_start)}–{formatTime(scene.time_end)}
          </p>
        </div>
      </div>

      {/* Intent */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">狙い</p>
        <p className="text-sm text-text-primary leading-relaxed">{scene.intent}</p>
      </div>

      {/* Composition */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">構図</p>
        <p className="text-sm text-text-primary leading-relaxed">{scene.composition}</p>
      </div>

      {/* Camera work */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
          カメラワーク
        </p>
        <p className="text-sm text-text-primary leading-relaxed">{scene.camera_work}</p>
      </div>

      {/* Text overlay */}
      {scene.text_overlay && (
        <div className="rounded-lg bg-background px-3 py-2">
          <span className="text-xs font-medium text-text-secondary">テロップ: </span>
          <span className="text-xs text-text-secondary">{scene.text_overlay}</span>
        </div>
      )}
    </div>
  )
}

export default function StoryboardView({
  projectId: _projectId,
  storyboard,
  structure,
  onRegenerate,
  onApprove,
  onRevise,
  isRegenerating,
  isApproving,
  isRevising,
  reviseError,
}: StoryboardViewProps) {
  const isApproved = storyboard.approved_at !== null
  const isPending = storyboard.status === 'pending'
  const isFailed = storyboard.status === 'failed'

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-text-primary">絵コンテ</h2>
          <span className="px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary">
            v{storyboard.version}
          </span>
        </div>
        {isApproved && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-xs font-medium text-green-400">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            承認済み
          </span>
        )}
      </div>

      {/* Pending state */}
      {isPending && (
        <div className="rounded-xl bg-surface border border-border p-8 flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-sm text-text-secondary">AIが絵コンテを生成しています...</p>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
          <p className="text-sm text-red-400">
            絵コンテの生成に失敗しました{storyboard.error_message ? `: ${storyboard.error_message}` : ''}
          </p>
        </div>
      )}

      {/* Feedback context, when this version is a revision */}
      {!isPending && !isFailed && storyboard.human_feedback && (
        <div className="rounded-xl bg-accent/5 border border-accent/20 p-5">
          <p className="text-xs font-medium text-accent mb-2 uppercase tracking-wider">
            フィードバックをもとに修正しました
          </p>
          <p className="text-sm text-text-primary leading-relaxed">{storyboard.human_feedback}</p>
        </div>
      )}

      {/* Scene strip (horizontal scroll, per ARCHITECTURE.md's コマ割り表示) */}
      {!isPending && !isFailed && (
        <div className="flex overflow-x-auto gap-4 pb-2">
          {storyboard.scenes.map((scene) => (
            <StoryboardSceneCard
              key={scene.scene_number}
              scene={scene}
              title={
                structure.scenes.find((s) => s.number === scene.scene_number)?.title ??
                `シーン${scene.scene_number}`
              }
            />
          ))}
        </div>
      )}

      {/* Request a revision (only once approved) */}
      {isApproved && (
        <RevisionFeedbackForm
          onSubmit={onRevise}
          isSubmitting={isRevising}
          disabled={isRegenerating || isApproving}
          error={reviseError}
          inputId="storyboard-revision-feedback"
          placeholder="例: シーン1のテロップをもっとシンプルにしてほしい"
        />
      )}

      {/* Footer actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button
          variant="secondary"
          onClick={onRegenerate}
          isLoading={isRegenerating}
          disabled={isRegenerating || isApproving || isPending || isRevising}
        >
          再生成する
        </Button>
        {!isApproved && !isPending && !isFailed && (
          <Button
            variant="primary"
            onClick={onApprove}
            isLoading={isApproving}
            disabled={isRegenerating || isApproving}
          >
            この絵コンテで進む
          </Button>
        )}
      </div>
    </div>
  )
}
