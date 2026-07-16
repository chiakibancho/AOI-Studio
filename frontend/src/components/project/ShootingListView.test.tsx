import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ShootingListView from './ShootingListView'
import type { ShootingList } from '@/types'

const baseShootingList: ShootingList = {
  id: 'sl1',
  project_id: 'p1',
  storyboard_id: 'sb1',
  shots: [
    {
      cut_number: 1,
      scene_number: 1,
      category: 'people',
      title: 'オフィス入口での挨拶ショット',
      location: 'オフィスエントランス',
      equipment: '一眼カメラ、ジンバル',
      talent_props: '出演者A',
      notes: '逆光に注意',
      completed: false,
    },
    {
      cut_number: 2,
      scene_number: 1,
      category: 'people',
      title: 'クローズアップ',
      location: 'オフィスエントランス',
      equipment: '一眼カメラ',
      talent_props: '出演者A',
      notes: '',
      completed: false,
    },
    {
      cut_number: 3,
      scene_number: 2,
      category: 'product',
      title: '商品カット',
      location: '会議室',
      equipment: '三脚',
      talent_props: '製品サンプル',
      notes: '',
      completed: true,
    },
  ],
  version: 1,
  status: 'completed',
  error_message: null,
  approved_at: null,
  generated_at: '2026-07-15T00:00:00Z',
}

function renderView(
  overrides: Partial<ShootingList> = {},
  handlers: {
    onApprove?: () => void
    onToggleShot?: (cutNumber: number, completed: boolean) => void
    onDownloadCsv?: () => void
  } = {}
) {
  return render(
    <ShootingListView
      projectId="p1"
      shootingList={{ ...baseShootingList, ...overrides }}
      onRegenerate={vi.fn()}
      onApprove={handlers.onApprove ?? vi.fn()}
      onToggleShot={handlers.onToggleShot ?? vi.fn()}
      onDownloadCsv={handlers.onDownloadCsv ?? vi.fn()}
      isRegenerating={false}
      isApproving={false}
    />
  )
}

describe('ShootingListView', () => {
  it('shows a loading state and no shots while pending', () => {
    renderView({ status: 'pending', shots: [] })

    expect(screen.getByText('AIが撮影リストを生成しています...')).toBeInTheDocument()
    expect(screen.queryByText('商品カット')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'CSVダウンロード' })).toBeDisabled()
  })

  it('enables the CSV download button when shots exist and calls the handler on click', () => {
    const onDownloadCsv = vi.fn()
    renderView({}, { onDownloadCsv })

    const button = screen.getByRole('button', { name: 'CSVダウンロード' })
    expect(button).not.toBeDisabled()
    fireEvent.click(button)
    expect(onDownloadCsv).toHaveBeenCalled()
  })

  it('keeps the CSV download button visible after approval', () => {
    renderView({ approved_at: '2026-07-15T01:00:00Z' })

    expect(screen.getByRole('button', { name: 'CSVダウンロード' })).not.toBeDisabled()
  })

  it('shows the error message when failed', () => {
    renderView({ status: 'failed', shots: [], error_message: 'Claude API エラー: 401' })

    expect(screen.getByText(/撮影リストの生成に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/Claude API エラー: 401/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).not.toBeDisabled()
  })

  it('groups shots by category and shows the completion count', () => {
    renderView()

    expect(screen.getByText('人物')).toBeInTheDocument()
    expect(screen.getByText('商品')).toBeInTheDocument()
    expect(screen.getByText('オフィス入口での挨拶ショット')).toBeInTheDocument()
    expect(screen.getByText('クローズアップ')).toBeInTheDocument()
    expect(screen.getByText('商品カット')).toBeInTheDocument()
    expect(screen.getByText('1/3 完了')).toBeInTheDocument()
  })

  it('calls onToggleShot with the cut_number and new completed value', () => {
    const onToggleShot = vi.fn()
    renderView({}, { onToggleShot })

    const checkbox = screen.getByLabelText('カット1を撮影完了にする')
    fireEvent.click(checkbox)

    expect(onToggleShot).toHaveBeenCalledWith(1, true)
  })

  it('shows an approve button when completed and not yet approved', () => {
    const onApprove = vi.fn()
    renderView({}, { onApprove })

    fireEvent.click(screen.getByRole('button', { name: 'この撮影リストで進む' }))
    expect(onApprove).toHaveBeenCalled()
  })

  it('hides the approve/regenerate buttons and shows a badge once approved, but keeps checkboxes usable', () => {
    const onToggleShot = vi.fn()
    renderView({ approved_at: '2026-07-15T01:00:00Z' }, { onToggleShot })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この撮影リストで進む' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '再生成する' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('カット1を撮影完了にする'))
    expect(onToggleShot).toHaveBeenCalledWith(1, true)
  })
})
