import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import StructureView from './StructureView'
import type { Structure } from '@/types'

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
  version: 1,
  status: 'completed',
  error_message: null,
  approved_at: null,
  generated_at: '2026-07-12T00:00:00Z',
}

function renderView(overrides: Partial<Structure> = {}) {
  return render(
    <StructureView
      projectId="p1"
      structure={{ ...baseStructure, ...overrides }}
      onRegenerate={vi.fn()}
      onApprove={vi.fn()}
      isRegenerating={false}
      isApproving={false}
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

  it('shows scenes and an approve button when completed and not yet approved', () => {
    renderView({ status: 'completed' })

    expect(screen.getByText('Opening')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'この構成で進む' })).toBeInTheDocument()
  })

  it('hides the approve button and shows a badge once approved', () => {
    renderView({ status: 'completed', approved_at: '2026-07-12T01:00:00Z' })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この構成で進む' })).not.toBeInTheDocument()
  })
})
