import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StructureView from './StructureView'
import type { Structure, StructureOption } from '@/types'

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
  ],
  rationale: 'because',
  total_duration_sec: 10,
  options: [],
  version: 1,
  status: 'completed',
  error_message: null,
  selected_option_index: null,
  human_feedback: null,
  based_on_structure_id: null,
  approved_at: null,
  generated_at: '2026-07-12T00:00:00Z',
}

const threeOptions: StructureOption[] = [
  {
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
    ],
    rationale: 'because-1',
    total_duration_sec: 10,
  },
  {
    scenes: [
      {
        number: 1,
        title: 'Problem',
        duration_sec: 12,
        description: 'desc-2',
        shot_type: 'Interview',
        mood: 'serious',
        notes: '',
      },
    ],
    rationale: 'because-2',
    total_duration_sec: 12,
  },
  {
    scenes: [
      {
        number: 1,
        title: 'Montage',
        duration_sec: 14,
        description: 'desc-3',
        shot_type: 'B-roll collage',
        mood: 'energetic',
        notes: '',
      },
    ],
    rationale: 'because-3',
    total_duration_sec: 14,
  },
]

function renderView(
  overrides: Partial<Structure> = {},
  handlers: {
    onApprove?: (optionIndex: number) => void
    onRevise?: (feedback: string) => void
  } = {},
  extraProps: { isRevising?: boolean; reviseError?: string | null } = {}
) {
  return render(
    <StructureView
      projectId="p1"
      structure={{ ...baseStructure, ...overrides }}
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

describe('StructureView', () => {
  it('shows a loading state and no scenes while pending', () => {
    renderView({ status: 'pending', scenes: [] })

    expect(screen.getByText('AIが構成を生成しています...')).toBeInTheDocument()
    expect(screen.queryByText('Opening')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'この構成で進む' })).not.toBeInTheDocument()
  })

  it('shows the error message and no approve button when failed', () => {
    renderView({ status: 'failed', scenes: [], error_message: 'Claude API エラー: 401' })

    expect(screen.getByText(/構成の生成に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/Claude API エラー: 401/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この構成で進む' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).not.toBeDisabled()
  })

  it('shows scenes and an approve button when completed with no options (legacy) and not yet approved', () => {
    renderView({ status: 'completed' })

    expect(screen.getByText('Opening')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'この構成で進む' })).toBeInTheDocument()
  })

  it('hides the approve button and shows a badge once approved', () => {
    renderView({ status: 'completed', approved_at: '2026-07-12T01:00:00Z' })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この構成で進む' })).not.toBeInTheDocument()
  })

  it('renders 3 option cards with a recommended badge on the first when completed and not approved', () => {
    renderView({ status: 'completed', options: threeOptions, scenes: [] })

    expect(screen.getByText('Opening')).toBeInTheDocument()
    expect(screen.getByText('Problem')).toBeInTheDocument()
    expect(screen.getByText('Montage')).toBeInTheDocument()
    expect(screen.getByText('おすすめ')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'この案を選ぶ' })).toHaveLength(3)
    expect(screen.queryByRole('button', { name: 'この構成で進む' })).not.toBeInTheDocument()
  })

  it('calls onApprove with the clicked option index', () => {
    const onApprove = vi.fn()
    renderView({ status: 'completed', options: threeOptions, scenes: [] }, { onApprove })

    const buttons = screen.getAllByRole('button', { name: 'この案を選ぶ' })
    fireEvent.click(buttons[2])

    expect(onApprove).toHaveBeenCalledWith(2)
  })

  it('falls back to the single confirmed view when approved even if options are present', () => {
    renderView({
      status: 'completed',
      options: threeOptions,
      scenes: threeOptions[2].scenes,
      rationale: threeOptions[2].rationale,
      total_duration_sec: threeOptions[2].total_duration_sec,
      selected_option_index: 2,
      approved_at: '2026-07-12T01:00:00Z',
    })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.getByText('Montage')).toBeInTheDocument()
    expect(screen.queryByText('Opening')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この案を選ぶ' })).not.toBeInTheDocument()
  })

  it('does not show the revision feedback form when not yet approved', () => {
    renderView({ status: 'completed' })

    expect(screen.queryByLabelText('修正を依頼する')).not.toBeInTheDocument()
  })

  it('shows the revision feedback form once approved and submits trimmed text', () => {
    const onRevise = vi.fn()
    renderView(
      { status: 'completed', approved_at: '2026-07-12T01:00:00Z' },
      { onRevise }
    )

    const textarea = screen.getByLabelText('修正を依頼する')
    fireEvent.change(textarea, { target: { value: '  シーン3をもう少し短くして  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'この内容で修正を依頼する' }))

    expect(onRevise).toHaveBeenCalledWith('シーン3をもう少し短くして')
  })

  it('disables the revision form while a revision is in flight', () => {
    renderView(
      { status: 'completed', approved_at: '2026-07-12T01:00:00Z' },
      {},
      { isRevising: true }
    )

    expect(screen.getByLabelText('修正を依頼する')).toBeDisabled()
  })

  it('shows feedback context when the version is a revision', () => {
    renderView({
      status: 'completed',
      approved_at: '2026-07-12T01:00:00Z',
      human_feedback: 'シーン3をもう少し短くして',
    })

    expect(screen.getByText('フィードバックをもとに修正しました')).toBeInTheDocument()
    expect(screen.getByText('シーン3をもう少し短くして')).toBeInTheDocument()
  })
})
