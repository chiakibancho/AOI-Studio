import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import SpecDraftView from './SpecDraftView'
import type { SpecDraft } from '@/types'

const baseDraft: SpecDraft = {
  id: 'd1',
  project_id: 'p1',
  raw_input: '採用動画を作りたい',
  duration_sec: 60,
  target_audience: '20代の求職者',
  message: '働きやすさを伝えたい',
  mood: 'friendly',
  style_notes: null,
  reference_urls: [],
  rationale: 'because',
  version: 1,
  status: 'completed',
  error_message: null,
  approved_at: null,
  generated_at: '2026-07-13T00:00:00Z',
}

function renderView(overrides: Partial<SpecDraft> = {}) {
  return render(
    <SpecDraftView
      draft={{ ...baseDraft, ...overrides }}
      onApprove={vi.fn()}
      onEditManually={vi.fn()}
      onRestart={vi.fn()}
      isApproving={false}
    />
  )
}

describe('SpecDraftView', () => {
  it('shows a loading state while pending', () => {
    renderView({ status: 'pending' })

    expect(screen.getByText('AIが仕様を分析しています...')).toBeInTheDocument()
    expect(screen.queryByText('働きやすさを伝えたい')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この内容で保存する' })).not.toBeInTheDocument()
  })

  it('shows the error message and a restart button when failed', () => {
    renderView({ status: 'failed', error_message: 'Claude API エラー: 401' })

    expect(screen.getByText(/仕様の分析に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/Claude API エラー: 401/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '入力からやり直す' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この内容で保存する' })).not.toBeInTheDocument()
  })

  it('shows the summary and both action buttons when completed', () => {
    renderView()

    expect(screen.getByText('働きやすさを伝えたい')).toBeInTheDocument()
    expect(screen.getByText('because')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '修正する' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'この内容で保存する' })).toBeInTheDocument()
  })
})
