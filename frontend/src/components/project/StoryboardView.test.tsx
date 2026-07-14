import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StoryboardView from './StoryboardView'
import type { Storyboard, Structure } from '@/types'

const baseStructure: Structure = {
  id: 's1',
  project_id: 'p1',
  scenes: [
    {
      number: 1,
      title: 'Opening',
      duration_sec: 10,
      description: 'desc',
      shot_type: 'B-roll',
      mood: 'calm',
      notes: '',
    },
    {
      number: 2,
      title: 'Closing',
      duration_sec: 5,
      description: 'desc-2',
      shot_type: 'B-roll',
      mood: 'warm',
      notes: '',
    },
  ],
  rationale: 'because',
  total_duration_sec: 15,
  options: [],
  version: 1,
  status: 'completed',
  error_message: null,
  selected_option_index: null,
  human_feedback: null,
  based_on_structure_id: null,
  approved_at: '2026-07-12T01:00:00Z',
  generated_at: '2026-07-12T00:00:00Z',
}

const baseStoryboard: Storyboard = {
  id: 'sb1',
  project_id: 'p1',
  structure_id: 's1',
  scenes: [
    {
      scene_number: 1,
      time_start: 0,
      time_end: 10,
      intent: '興味を引く',
      composition: '人物クローズアップ',
      camera_work: '静止からズームイン',
      text_overlay: 'あなたの仕事を、もっと自由に。',
    },
    {
      scene_number: 2,
      time_start: 10,
      time_end: 15,
      intent: '余韻を残す',
      composition: 'オフィス全景',
      camera_work: 'ゆっくりパン',
      text_overlay: '',
    },
  ],
  version: 1,
  status: 'completed',
  error_message: null,
  human_feedback: null,
  based_on_storyboard_id: null,
  approved_at: null,
  generated_at: '2026-07-13T00:00:00Z',
}

function renderView(
  overrides: Partial<Storyboard> = {},
  handlers: {
    onApprove?: () => void
    onRevise?: (feedback: string) => void
  } = {},
  extraProps: { isRevising?: boolean; reviseError?: string | null } = {}
) {
  return render(
    <StoryboardView
      projectId="p1"
      storyboard={{ ...baseStoryboard, ...overrides }}
      structure={baseStructure}
      onRegenerate={vi.fn()}
      onApprove={handlers.onApprove ?? vi.fn()}
      onRevise={handlers.onRevise ?? vi.fn()}
      isRegenerating={false}
      isApproving={false}
      isRevising={extraProps.isRevising ?? false}
      reviseError={extraProps.reviseError ?? null}
    />
  )
}

describe('StoryboardView', () => {
  it('shows a loading state and no scenes while pending', () => {
    renderView({ status: 'pending', scenes: [] })

    expect(screen.getByText('AIが絵コンテを生成しています...')).toBeInTheDocument()
    expect(screen.queryByText('Opening')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'この絵コンテで進む' })).not.toBeInTheDocument()
  })

  it('shows the error message and no approve button when failed', () => {
    renderView({ status: 'failed', scenes: [], error_message: 'Claude API エラー: 401' })

    expect(screen.getByText(/絵コンテの生成に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/Claude API エラー: 401/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この絵コンテで進む' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).not.toBeDisabled()
  })

  it('shows scene cards cross-referenced to structure titles, and an approve button', () => {
    renderView()

    expect(screen.getByText('Opening')).toBeInTheDocument()
    expect(screen.getByText('Closing')).toBeInTheDocument()
    expect(screen.getByText('0:00–0:10')).toBeInTheDocument()
    expect(screen.getByText('人物クローズアップ')).toBeInTheDocument()
    expect(screen.getByText(/あなたの仕事を、もっと自由に。/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'この絵コンテで進む' })).toBeInTheDocument()
  })

  it('falls back to a generic scene label when no matching structure scene is found', () => {
    renderView({
      scenes: [
        {
          scene_number: 99,
          time_start: 0,
          time_end: 5,
          intent: 'x',
          composition: 'x',
          camera_work: 'x',
          text_overlay: '',
        },
      ],
    })

    expect(screen.getByText('シーン99')).toBeInTheDocument()
  })

  it('calls onApprove when the approve button is clicked', () => {
    const onApprove = vi.fn()
    renderView({}, { onApprove })

    fireEvent.click(screen.getByRole('button', { name: 'この絵コンテで進む' }))

    expect(onApprove).toHaveBeenCalled()
  })

  it('hides the approve/regenerate buttons and shows a badge once approved, with only the scene strip visible', () => {
    renderView({ approved_at: '2026-07-13T01:00:00Z' })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.getByText('Opening')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この絵コンテで進む' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '再生成する' })).not.toBeInTheDocument()
  })

  it('does not show the revision feedback form regardless of approval state', () => {
    renderView()
    expect(screen.queryByLabelText('修正を依頼する')).not.toBeInTheDocument()

    renderView({ approved_at: '2026-07-13T01:00:00Z' })
    expect(screen.queryByLabelText('修正を依頼する')).not.toBeInTheDocument()
  })

  it('shows feedback context when the version is a revision', () => {
    renderView({
      approved_at: '2026-07-13T01:00:00Z',
      human_feedback: 'テロップをもっとシンプルに',
    })

    expect(screen.getByText('フィードバックをもとに修正しました')).toBeInTheDocument()
    expect(screen.getByText('テロップをもっとシンプルに')).toBeInTheDocument()
  })
})
