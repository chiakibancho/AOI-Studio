'use client'

import type { ShootingList, ShootingListShot, ShotCategory } from '@/types'
import { SHOT_CATEGORY_LABELS, SHOT_CATEGORY_ORDER } from '@/types'
import Button from '@/components/ui/Button'

interface ShootingListViewProps {
  projectId: string
  shootingList: ShootingList
  onRegenerate: () => void
  onApprove: () => void
  onToggleShot: (cutNumber: number, completed: boolean) => void
  onDownloadCsv: () => void
  isRegenerating: boolean
  isApproving: boolean
}

function ShotRow({
  shot,
  onToggle,
}: {
  shot: ShootingListShot
  onToggle: (completed: boolean) => void
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={shot.completed}
          onChange={(e) => onToggle(e.target.checked)}
          className="mt-1 w-5 h-5 flex-shrink-0 accent-accent"
          aria-label={`カット${shot.cut_number}を撮影完了にする`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded bg-background border border-border text-xs font-bold text-text-primary">
              #{shot.cut_number}
            </span>
            <span className="text-xs text-text-secondary">シーン{shot.scene_number}</span>
            {shot.completed && (
              <span className="text-xs font-medium text-green-400">撮影済み</span>
            )}
          </div>
          <p
            className={`font-semibold text-sm mt-1 ${
              shot.completed ? 'text-text-secondary line-through' : 'text-text-primary'
            }`}
          >
            {shot.title}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-8">
        <div>
          <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
            ロケーション
          </p>
          <p className="text-sm text-text-primary leading-relaxed">{shot.location}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
            機材
          </p>
          <p className="text-sm text-text-primary leading-relaxed">{shot.equipment}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
            出演者・小道具
          </p>
          <p className="text-sm text-text-primary leading-relaxed">{shot.talent_props}</p>
        </div>
        {shot.notes && (
          <div>
            <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
              注意点
            </p>
            <p className="text-sm text-text-primary leading-relaxed">{shot.notes}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ShootingListView({
  projectId: _projectId,
  shootingList,
  onRegenerate,
  onApprove,
  onToggleShot,
  onDownloadCsv,
  isRegenerating,
  isApproving,
}: ShootingListViewProps) {
  const isApproved = shootingList.approved_at !== null
  const isPending = shootingList.status === 'pending'
  const isFailed = shootingList.status === 'failed'

  const totalCount = shootingList.shots.length
  const completedCount = shootingList.shots.filter((s) => s.completed).length

  const shotsByCategory = new Map<ShotCategory, ShootingListShot[]>()
  for (const shot of shootingList.shots) {
    const list = shotsByCategory.get(shot.category) ?? []
    list.push(shot)
    shotsByCategory.set(shot.category, list)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-text-primary">撮影リスト</h2>
          <span className="px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary">
            v{shootingList.version}
          </span>
          {!isPending && !isFailed && (
            <span className="text-sm text-text-secondary">
              {completedCount}/{totalCount} 完了
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={onDownloadCsv}
            disabled={totalCount === 0}
          >
            CSVダウンロード
          </Button>
          {isApproved && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-xs font-medium text-green-400">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              承認済み
            </span>
          )}
        </div>
      </div>

      {/* Pending state */}
      {isPending && (
        <div className="rounded-xl bg-surface border border-border p-8 flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-sm text-text-secondary">AIが撮影リストを生成しています...</p>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
          <p className="text-sm text-red-400">
            撮影リストの生成に失敗しました{shootingList.error_message ? `: ${shootingList.error_message}` : ''}
          </p>
        </div>
      )}

      {/* Category-grouped checklist (mobile-first: stacked sections, per ARCHITECTURE.md's /shooting モバイル対応) */}
      {!isPending && !isFailed && (
        <div className="flex flex-col gap-6">
          {SHOT_CATEGORY_ORDER.filter((category) => shotsByCategory.has(category)).map((category) => (
            <div key={category} className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-text-primary">
                {SHOT_CATEGORY_LABELS[category]}
              </h3>
              <div className="flex flex-col gap-3">
                {shotsByCategory.get(category)!.map((shot) => (
                  <ShotRow
                    key={shot.cut_number}
                    shot={shot}
                    onToggle={(completed) => onToggleShot(shot.cut_number, completed)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer actions — hidden once approved */}
      {!isApproved && (
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={onRegenerate}
            isLoading={isRegenerating}
            disabled={isRegenerating || isApproving || isPending}
          >
            再生成する
          </Button>
          {!isPending && !isFailed && (
            <Button
              variant="primary"
              onClick={onApprove}
              isLoading={isApproving}
              disabled={isRegenerating || isApproving}
            >
              この撮影リストで進む
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
