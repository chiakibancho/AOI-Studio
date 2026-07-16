import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CharacterBibleView from './CharacterBibleView'
import type { Character } from '@/types'

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: new Blob() })),
  },
}))

const baseCharacter: Character = {
  id: 'c1',
  project_id: 'p1',
  name: 'Alice',
  prompt: 'A character with red hair',
  sheet_image_path: null,
  status: 'draft',
  error_message: null,
  approved_at: null,
  created_at: '2026-07-16T00:00:00Z',
  updated_at: '2026-07-16T00:00:00Z',
}

function renderView(
  props: Partial<React.ComponentProps<typeof CharacterBibleView>> = {}
) {
  return render(
    <CharacterBibleView
      characters={[]}
      onCreate={vi.fn()}
      onGenerate={vi.fn()}
      onApprove={vi.fn()}
      isCreating={false}
      createError={null}
      actionError={null}
      pendingCharacterId={null}
      {...props}
    />
  )
}

describe('CharacterBibleView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls onCreate with the name and prompt when Generate is clicked', () => {
    const onCreate = vi.fn()
    renderView({ onCreate })

    fireEvent.change(screen.getByRole('textbox', { name: 'キャラクター名' }), {
      target: { value: 'Alice' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Character Prompt' }), {
      target: { value: 'A character with red hair' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(onCreate).toHaveBeenCalledWith('Alice', 'A character with red hair')
  })

  it('appends filled Advanced fields to the prompt, in order, when creating', () => {
    const onCreate = vi.fn()
    renderView({ onCreate })

    fireEvent.change(screen.getByRole('textbox', { name: 'キャラクター名' }), {
      target: { value: 'Alice' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Character Prompt' }), {
      target: { value: 'Base description.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Advanced/ }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Face' }), {
      target: { value: 'oval, freckles' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Body' }), {
      target: { value: 'slim' },
    })
    // Hair と Clothes は未入力のまま

    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(onCreate).toHaveBeenCalledWith(
      'Alice',
      'Base description.\nFace: oval, freckles\nBody: slim'
    )
  })

  it('does not append anything when Advanced fields are left empty', () => {
    const onCreate = vi.fn()
    renderView({ onCreate })

    fireEvent.change(screen.getByRole('textbox', { name: 'キャラクター名' }), {
      target: { value: 'Alice' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Character Prompt' }), {
      target: { value: 'Base description.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(onCreate).toHaveBeenCalledWith('Alice', 'Base description.')
  })

  it('shows a spinner while a character is generating', () => {
    renderView({ characters: [{ ...baseCharacter, status: 'generating' }] })

    expect(screen.getByText('モデルシートを生成しています...')).toBeInTheDocument()
  })

  it('shows the generate button for draft characters and calls onGenerate', () => {
    const onGenerate = vi.fn()
    renderView({ characters: [baseCharacter], onGenerate })

    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))
    expect(onGenerate).toHaveBeenCalledWith('c1')
  })

  it('shows the approve button for generated characters and calls onApprove', () => {
    const onApprove = vi.fn()
    renderView({ characters: [{ ...baseCharacter, status: 'generated' }], onApprove })

    fireEvent.click(screen.getByRole('button', { name: '承認する' }))
    expect(onApprove).toHaveBeenCalledWith('c1')
  })

  it('hides generate/approve buttons and shows a badge once approved', () => {
    renderView({ characters: [{ ...baseCharacter, status: 'approved' }] })

    expect(screen.getAllByText('承認済み').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: '再生成する' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '承認する' })).not.toBeInTheDocument()
  })

  it('shows the error message for a failed character', () => {
    renderView({
      characters: [{ ...baseCharacter, status: 'failed', error_message: 'Together AI エラー: 500' }],
    })

    expect(screen.getByText('Together AI エラー: 500')).toBeInTheDocument()
  })
})
