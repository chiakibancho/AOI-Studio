'use client'

import { useEffect, useState } from 'react'
import type { Character } from '@/types'
import api from '@/lib/api'
import Button from '@/components/ui/Button'

interface CharacterBibleViewProps {
  characters: Character[]
  templateVariables: string[]
  onCreate: (name: string, variables: Record<string, string>) => void
  onGenerate: (characterId: string) => void
  onApprove: (characterId: string) => void
  isCreating: boolean
  createError: string | null
  actionError: string | null
  pendingCharacterId: string | null
}

const STATUS_LABELS: Record<Character['status'], string> = {
  draft: '未生成',
  generating: '生成中',
  generated: '生成済み',
  failed: '生成失敗',
  approved: '承認済み',
}

function formatLabel(variable: string): string {
  return variable
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

const SEPARATOR_CHARS = /[\s:\-=]/

/**
 * "Name: Alice\nFace Shape: oval\n..." のような、フィールド名から始まる塊を
 * テンプレート変数のキーにマッピングする。
 *
 * フィールド境界はテキスト全体を1つの文字列として走査して検出する（行頭に限定しない）。
 * 貼り付け元（チャットのレンダリング結果など）によっては改行が失われ、ある項目の値の
 * 直後に次のフィールド名が改行なしで連結されることがあるため、行単位ではなく
 * 「既知フィールド名 + 区切り文字（コロン/スペース/ハイフン等）」の出現位置そのものを
 * 境界として扱う。値は、ある境界の直後から次の境界の直前までとする。
 *
 * 戻り値には一致したキーのみを含む（未一致のフィールドはキーごと含まれない）。
 */
export function parseCharacterText(
  text: string,
  templateVariables: string[]
): Record<string, string> {
  const fieldLookup = new Map<string, string>()
  fieldLookup.set('name', 'name')
  for (const variable of templateVariables) {
    fieldLookup.set(variable.toLowerCase().replace(/_/g, ' '), variable)
    // "HAIR_STYLE:" のようにテンプレート変数名がそのままラベルとして貼り付けられる
    // ケースにも対応する（スペース区切りに加えてアンダースコア区切りも許容）。
    fieldLookup.set(variable.toLowerCase(), variable)
  }
  // より具体的な(長い)ラベルから優先的にマッチさせる
  const labels = Array.from(fieldLookup.keys()).sort((a, b) => b.length - a.length)

  const lowerText = text.toLowerCase()

  interface Boundary {
    key: string
    matchStart: number
    valueStart: number
  }
  const boundaries: Boundary[] = []

  for (let i = 0; i < lowerText.length; i++) {
    // 直前が英字なら単語の途中なのでラベルの開始位置として扱わない
    if (i > 0 && /[a-z]/.test(lowerText[i - 1])) continue

    for (const label of labels) {
      if (!lowerText.startsWith(label, i)) continue
      const afterLabel = i + label.length
      const nextChar = lowerText.charAt(afterLabel)
      if (nextChar !== '' && !SEPARATOR_CHARS.test(nextChar)) continue

      let valueStart = afterLabel
      while (valueStart < text.length && SEPARATOR_CHARS.test(lowerText[valueStart])) {
        valueStart++
      }
      boundaries.push({ key: fieldLookup.get(label) as string, matchStart: i, valueStart })
      break
    }
  }

  const result: Record<string, string> = {}
  for (let i = 0; i < boundaries.length; i++) {
    const boundary = boundaries[i]
    const end = i + 1 < boundaries.length ? boundaries[i + 1].matchStart : text.length
    const value = text.slice(boundary.valueStart, end).trim()
    if (value) {
      result[boundary.key] = value
    }
  }

  // EYE_SHAPE フォールバック: 貼り付け元のテキストで "Eye Shape" のラベル自体が
  // 省略され、Eye Color の直前の行が実質的な目の形状の説明になっているケースがある。
  // その場合、直前フィールドの値の最終行を EYE_SHAPE として切り出す。
  if (templateVariables.includes('EYE_SHAPE') && !('EYE_SHAPE' in result)) {
    const eyeColorIndex = boundaries.findIndex((b) => b.key === 'EYE_COLOR')
    if (eyeColorIndex > 0) {
      const prevKey = boundaries[eyeColorIndex - 1].key
      const prevValue = result[prevKey]
      if (prevValue && prevValue.includes('\n')) {
        const lines = prevValue.split('\n')
        const lastLine = (lines.pop() as string).trim()
        if (lastLine) {
          result.EYE_SHAPE = lastLine
          result[prevKey] = lines.join('\n').trim()
        }
      }
    }
  }

  return result
}

function CharacterSheetImage({ character }: { character: Character }) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  useEffect(() => {
    if (character.status !== 'generated' && character.status !== 'approved') {
      setImageUrl(null)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    api
      .get(`/api/v1/characters/${character.id}/sheet-image`, { responseType: 'blob' })
      .then((res) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(res.data)
        setImageUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setImageUrl(null)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [character.id, character.status])

  if (!imageUrl) return null
  return (
    <img
      src={imageUrl}
      alt={`${character.name}のモデルシート`}
      className="w-full rounded-lg border border-border"
    />
  )
}

function CharacterCard({
  character,
  onGenerate,
  onApprove,
  isBusy,
}: {
  character: Character
  onGenerate: () => void
  onApprove: () => void
  isBusy: boolean
}) {
  const isGenerating = character.status === 'generating'
  const isApproved = character.status === 'approved'
  const canGenerate = character.status !== 'approved' && character.status !== 'generating'

  return (
    <div className="rounded-xl border border-border bg-background p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-text-primary">{character.name}</span>
        <span className="px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary">
          {STATUS_LABELS[character.status]}
        </span>
      </div>

      {isGenerating && (
        <div className="rounded-lg bg-surface border border-border p-6 flex flex-col items-center gap-2">
          <div className="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-xs text-text-secondary">モデルシートを生成しています...</p>
        </div>
      )}

      {character.status === 'failed' && character.error_message && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2">
          <p className="text-xs text-red-400">{character.error_message}</p>
        </div>
      )}

      <CharacterSheetImage character={character} />

      <div className="flex items-center gap-2">
        {canGenerate && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onGenerate}
            isLoading={isBusy}
            disabled={isBusy}
          >
            {character.status === 'draft' ? '生成する' : '再生成する'}
          </Button>
        )}
        {character.status === 'generated' && (
          <Button variant="primary" size="sm" onClick={onApprove} isLoading={isBusy} disabled={isBusy}>
            承認する
          </Button>
        )}
        {isApproved && <span className="text-xs font-medium text-green-400">承認済み</span>}
      </div>
    </div>
  )
}

export default function CharacterBibleView({
  characters,
  templateVariables,
  onCreate,
  onGenerate,
  onApprove,
  isCreating,
  createError,
  actionError,
  pendingCharacterId,
}: CharacterBibleViewProps) {
  const [showForm, setShowForm] = useState(characters.length === 0)
  const [name, setName] = useState('')
  const [variables, setVariables] = useState<Record<string, string>>({})
  const [showBulkInput, setShowBulkInput] = useState(false)
  const [bulkText, setBulkText] = useState('')

  function handleVariableChange(key: string, value: string) {
    setVariables((prev) => ({ ...prev, [key]: value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onCreate(name, variables)
  }

  function handleApplyBulkText() {
    const parsed = parseCharacterText(bulkText, templateVariables)
    const { name: parsedName, ...parsedVariables } = parsed
    if (parsedName) {
      setName(parsedName)
    }
    setVariables((prev) => ({ ...prev, ...parsedVariables }))
    setShowBulkInput(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-text-primary">キャラクター</h2>
        <Button variant="secondary" size="sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? '閉じる' : '+ 新しいキャラクター'}
        </Button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-background p-4 flex flex-col gap-3"
        >
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <button
              type="button"
              onClick={() => setShowBulkInput((v) => !v)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-text-secondary hover:text-text-primary"
            >
              <span>キャラ設定をテキストで貼り付け</span>
              <span>{showBulkInput ? '▲' : '▼'}</span>
            </button>
            {showBulkInput && (
              <div className="px-3 pb-3 flex flex-col gap-2">
                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  rows={8}
                  aria-label="キャラ設定テキスト"
                  placeholder={'Name: Alice\nFace Shape: oval\nEye Color: brown\n...'}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text-primary"
                />
                <div className="flex justify-end">
                  <Button type="button" variant="secondary" size="sm" onClick={handleApplyBulkText}>
                    フィールドに反映する
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="text-xs font-medium text-text-secondary mb-1 block">名前</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              aria-label="名前"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary"
            />
          </div>
          {templateVariables.map((variable) => (
            <div key={variable}>
              <label className="text-xs font-medium text-text-secondary mb-1 block">
                {formatLabel(variable)}
              </label>
              <input
                type="text"
                value={variables[variable] ?? ''}
                onChange={(e) => handleVariableChange(variable, e.target.value)}
                required
                aria-label={formatLabel(variable)}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary"
              />
            </div>
          ))}
          {createError && <p className="text-sm text-red-400">{createError}</p>}
          <Button type="submit" variant="primary" size="sm" isLoading={isCreating} disabled={isCreating}>
            作成する
          </Button>
        </form>
      )}

      {actionError && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
          <p className="text-sm text-red-400">{actionError}</p>
        </div>
      )}

      {characters.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {characters.map((character) => (
            <CharacterCard
              key={character.id}
              character={character}
              onGenerate={() => onGenerate(character.id)}
              onApprove={() => onApprove(character.id)}
              isBusy={pendingCharacterId === character.id}
            />
          ))}
        </div>
      )}
    </div>
  )
}
