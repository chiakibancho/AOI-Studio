'use client'

import type { Structure } from '@/types'
import Button from '@/components/ui/Button'

interface StructureViewProps {
  projectId: string
  structure: Structure
  onRegenerate: () => void
  onApprove: () => void
  isRegenerating: boolean
  isApproving: boolean
}

export default function StructureView({
  projectId: _projectId,
  structure,
  onRegenerate,
  onApprove,
  isRegenerating,
  isApproving,
}: StructureViewProps) {
  const isApproved = structure.approved_at !== null

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-text-primary">AI構成提案</h2>
          <span className="px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary">
            v{structure.version}
          </span>
          <span className="text-sm text-text-secondary">
            合計 {structure.total_duration_sec}秒
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

      {/* Rationale */}
      <div className="rounded-xl bg-surface border border-border p-5">
        <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wider">
          構成の意図
        </p>
        <p className="text-sm text-text-primary leading-relaxed">{structure.rationale}</p>
      </div>

      {/* Scene list */}
      <div className="flex flex-col gap-4">
        {structure.scenes.map((scene) => (
          <div
            key={scene.number}
            className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-3"
          >
            {/* Scene header */}
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center">
                <span className="text-xs font-bold text-white">{scene.number}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-text-primary text-sm">{scene.title}</span>
                  <span className="text-xs text-text-secondary">{scene.duration_sec}s</span>
                </div>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-background border border-border text-xs text-text-secondary">
                    {scene.shot_type}
                  </span>
                  <span className="text-xs text-text-secondary">{scene.mood}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="text-sm text-text-primary leading-relaxed pl-10">
              {scene.description}
            </p>

            {/* Notes */}
            {scene.notes && (
              <div className="pl-10">
                <div className="rounded-lg bg-background px-3 py-2">
                  <span className="text-xs font-medium text-text-secondary">メモ: </span>
                  <span className="text-xs text-text-secondary">{scene.notes}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button
          variant="secondary"
          onClick={onRegenerate}
          isLoading={isRegenerating}
          disabled={isRegenerating || isApproving}
        >
          再生成する
        </Button>
        {!isApproved && (
          <Button
            variant="primary"
            onClick={onApprove}
            isLoading={isApproving}
            disabled={isRegenerating || isApproving}
          >
            この構成で進む
          </Button>
        )}
      </div>
    </div>
  )
}
