'use client'

import type { SpecDraft } from '@/types'
import { MOOD_OPTIONS } from '@/types'
import Button from '@/components/ui/Button'

interface SpecDraftViewProps {
  draft: SpecDraft
  onApprove: () => void
  onEditManually: () => void
  onRestart: (rawInputSeed: string) => void
  isApproving: boolean
}

export default function SpecDraftView({
  draft,
  onApprove,
  onEditManually,
  onRestart,
  isApproving,
}: SpecDraftViewProps) {
  const isPending = draft.status === 'pending'
  const isFailed = draft.status === 'failed'
  const moodLabel = MOOD_OPTIONS.find((opt) => opt.value === draft.mood)?.label ?? draft.mood

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-text-primary">AI仕様サマリー</h2>
          <span className="px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary">
            v{draft.version}
          </span>
        </div>
      </div>

      {/* Pending state */}
      {isPending && (
        <div className="rounded-xl bg-surface border border-border p-8 flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-sm text-text-secondary">AIが仕様を分析しています...</p>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div className="flex flex-col gap-3">
          <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
            <p className="text-sm text-red-400">
              仕様の分析に失敗しました{draft.error_message ? `: ${draft.error_message}` : ''}
            </p>
          </div>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => onRestart(draft.raw_input)}>
              入力からやり直す
            </Button>
          </div>
        </div>
      )}

      {!isPending && !isFailed && (
        <>
          {/* Rationale */}
          <div className="rounded-xl bg-surface border border-border p-5">
            <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wider">
              AIの解釈
            </p>
            <p className="text-sm text-text-primary leading-relaxed">{draft.rationale}</p>
          </div>

          {/* Structured summary */}
          <div className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-4">
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="px-2.5 py-1 rounded-lg bg-background border border-border text-text-primary">
                {draft.duration_sec}秒
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-background border border-border text-text-primary">
                {moodLabel}
              </span>
            </div>

            <div>
              <p className="text-xs font-medium text-text-secondary mb-1">ターゲット層</p>
              <p className="text-sm text-text-primary leading-relaxed">{draft.target_audience}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-text-secondary mb-1">伝えたいメッセージ</p>
              <p className="text-sm text-text-primary leading-relaxed">{draft.message}</p>
            </div>

            {draft.style_notes && (
              <div>
                <p className="text-xs font-medium text-text-secondary mb-1">スタイル補足</p>
                <p className="text-sm text-text-primary leading-relaxed">{draft.style_notes}</p>
              </div>
            )}

            {draft.reference_urls.length > 0 && (
              <div>
                <p className="text-xs font-medium text-text-secondary mb-1">参考URL</p>
                <ul className="flex flex-col gap-1">
                  {draft.reference_urls.map((url) => (
                    <li key={url} className="text-sm text-accent truncate">
                      {url}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </>
      )}

      {/* Footer actions */}
      {!isPending && !isFailed && (
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={onEditManually}
            disabled={isApproving}
          >
            修正する
          </Button>
          <Button
            variant="primary"
            onClick={onApprove}
            isLoading={isApproving}
            disabled={isApproving}
          >
            この内容で保存する
          </Button>
        </div>
      )}
    </div>
  )
}
