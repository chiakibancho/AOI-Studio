import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CharacterBibleView, { parseCharacterText } from './CharacterBibleView'
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
  variables: { FACE_SHAPE: 'oval' },
  template_version: 'v1',
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
      templateVariables={['FACE_SHAPE', 'EYE_COLOR']}
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

  it('builds a form field for each template variable', () => {
    renderView()

    expect(screen.getByText('名前')).toBeInTheDocument()
    expect(screen.getByText('Face Shape')).toBeInTheDocument()
    expect(screen.getByText('Eye Color')).toBeInTheDocument()
  })

  it('calls onCreate with the name and variables on submit', () => {
    const onCreate = vi.fn()
    renderView({ onCreate })

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: 'Alice' } })
    fireEvent.change(inputs[1], { target: { value: 'oval' } })
    fireEvent.change(inputs[2], { target: { value: 'blue' } })

    fireEvent.click(screen.getByRole('button', { name: '作成する' }))

    expect(onCreate).toHaveBeenCalledWith('Alice', { FACE_SHAPE: 'oval', EYE_COLOR: 'blue' })
  })

  it('shows a spinner while a character is generating', () => {
    renderView({ characters: [{ ...baseCharacter, status: 'generating' }] })

    expect(screen.getByText('モデルシートを生成しています...')).toBeInTheDocument()
  })

  it('shows the generate button for draft characters and calls onGenerate', () => {
    const onGenerate = vi.fn()
    renderView({ characters: [baseCharacter], onGenerate })

    fireEvent.click(screen.getByRole('button', { name: '生成する' }))
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

  it('applies pasted text to matching fields via the bulk input section', () => {
    renderView({ templateVariables: ['FACE_SHAPE', 'EYE_COLOR', 'ART_STYLE'] })

    fireEvent.click(screen.getByRole('button', { name: /キャラ設定をテキストで貼り付け/ }))

    const bulkTextarea = screen.getByRole('textbox', { name: 'キャラ設定テキスト' })
    fireEvent.change(bulkTextarea, {
      target: {
        value: 'Name: Alice\nFace Shape: oval\nEye Color: brown\nArt Style: clean digital anime style',
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'フィールドに反映する' }))

    expect(screen.getByRole('textbox', { name: '名前' })).toHaveValue('Alice')
    expect(screen.getByRole('textbox', { name: 'Face Shape' })).toHaveValue('oval')
    expect(screen.getByRole('textbox', { name: 'Art Style' })).toHaveValue('clean digital anime style')
  })

  it('does not clear fields left unmatched by the pasted text', () => {
    renderView({ templateVariables: ['FACE_SHAPE', 'EYE_COLOR', 'ART_STYLE'] })

    fireEvent.change(screen.getByRole('textbox', { name: 'Eye Color' }), {
      target: { value: 'brown' },
    })

    fireEvent.click(screen.getByRole('button', { name: /キャラ設定をテキストで貼り付け/ }))
    const bulkTextarea = screen.getByRole('textbox', { name: 'キャラ設定テキスト' })
    fireEvent.change(bulkTextarea, {
      target: {
        value: 'Some unrelated preamble that matches no known field.\nFace Shape: oval',
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'フィールドに反映する' }))

    expect(screen.getByRole('textbox', { name: 'Face Shape' })).toHaveValue('oval')
    expect(screen.getByRole('textbox', { name: 'Eye Color' })).toHaveValue('brown')
  })
})

describe('parseCharacterText', () => {
  const FULL_TEMPLATE_VARIABLES = [
    'FACE_SHAPE',
    'EYE_SHAPE',
    'EYE_COLOR',
    'EYEBROWS',
    'NOSE',
    'MOUTH',
    'SKIN',
    'HAIR_STYLE',
    'HAIR_LENGTH',
    'HAIR_COLOR',
    'BANGS',
    'HEIGHT',
    'BODY_TYPE',
    'SHOULDER_WIDTH',
    'HAND_SIZE',
    'LEG_LENGTH',
    'TOP',
    'BOTTOM',
    'SHOES',
    'ACCESSORIES',
    'PRIMARY_COLOR',
    'SECONDARY_COLOR',
    'ACCENT_COLOR',
    'ART_STYLE',
  ]

  it('separates SKIN from HAIR_STYLE even without a blank line between them', () => {
    const text = [
      'Face Shape Slim oval face...',
      'Eye Color Deep gray-brown',
      'Eyebrows Neat, slightly arched',
      'Skin Fair, pale',
      'Hair Style Medium-length black hair...',
    ].join('\n')

    const parsed = parseCharacterText(text, FULL_TEMPLATE_VARIABLES)

    expect(parsed.SKIN).toBe('Fair, pale')
    expect(parsed.HAIR_STYLE).toBe('Medium-length black hair...')
  })

  it('separates fields even when pasted as a single line with no newlines', () => {
    const text =
      'Face Shape Slim oval face... Eye Color Deep gray-brown Eyebrows Neat, slightly arched ' +
      'Skin Fair, pale Hair Style Medium-length black hair...'

    const parsed = parseCharacterText(text, FULL_TEMPLATE_VARIABLES)

    expect(parsed.SKIN).toBe('Fair, pale')
    expect(parsed.HAIR_STYLE).toBe('Medium-length black hair...')
  })

  it('recognizes a raw underscored template variable name as a field label too', () => {
    const text = 'Skin Fair, pale\nHAIR_STYLE: Medium-length black hair...'

    const parsed = parseCharacterText(text, FULL_TEMPLATE_VARIABLES)

    expect(parsed.SKIN).toBe('Fair, pale')
    expect(parsed.HAIR_STYLE).toBe('Medium-length black hair...')
  })

  it('falls back to the line before Eye Color as EYE_SHAPE when the label is omitted', () => {
    const text = [
      'Face Shape Slim oval face',
      'Slightly almond-shaped, upturned outer corners',
      'Eye Color Deep gray-brown',
    ].join('\n')

    const parsed = parseCharacterText(text, FULL_TEMPLATE_VARIABLES)

    expect(parsed.EYE_SHAPE).toBe('Slightly almond-shaped, upturned outer corners')
    expect(parsed.FACE_SHAPE).toBe('Slim oval face')
    expect(parsed.EYE_COLOR).toBe('Deep gray-brown')
  })

  it('does not invent an EYE_SHAPE value when there is no orphan line before Eye Color', () => {
    const text = ['Face Shape Slim oval face', 'Eye Color Deep gray-brown'].join('\n')

    const parsed = parseCharacterText(text, FULL_TEMPLATE_VARIABLES)

    expect(parsed.EYE_SHAPE).toBeUndefined()
    expect(parsed.FACE_SHAPE).toBe('Slim oval face')
  })
})
