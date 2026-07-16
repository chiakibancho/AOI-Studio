'use client'

import { useRef, useState } from 'react'
import type { MusicAnalysis } from '@/types'
import Button from '@/components/ui/Button'

interface MusicAnalysisViewProps {
  musicAnalysis: MusicAnalysis | null
  onUpload: (file: File) => void
  isUploading: boolean
  error: string | null
}

export default function MusicAnalysisView({
  musicAnalysis,
  onUpload,
  isUploading,
  error,
}: MusicAnalysisViewProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSelectedFile(e.target.files?.[0] ?? null)
  }

  function handleUpload() {
    if (!selectedFile) return
    onUpload(selectedFile)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-bold text-text-primary">BGM解析</h2>
        {musicAnalysis && (
          <span className="text-xs text-text-secondary">{musicAnalysis.filename}</span>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          ref={inputRef}
          type="file"
          accept=".mp3,.wav,audio/mpeg,audio/wav"
          onChange={handleFileChange}
          aria-label="BGMファイルを選択"
          className="text-sm text-text-secondary file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-border file:bg-surface file:text-text-primary file:text-sm hover:file:bg-border"
        />
        <Button
          variant="primary"
          size="sm"
          onClick={handleUpload}
          isLoading={isUploading}
          disabled={!selectedFile || isUploading}
        >
          解析する
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {musicAnalysis && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-border bg-background p-4">
            <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
              BPM
            </p>
            <p className="text-2xl font-bold text-text-primary">{Math.round(musicAnalysis.bpm)}</p>
          </div>
          <div className="rounded-xl border border-border bg-background p-4">
            <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
              キー
            </p>
            <p className="text-2xl font-bold text-text-primary">
              {musicAnalysis.key} {musicAnalysis.scale === 'major' ? 'メジャー' : 'マイナー'}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-background p-4">
            <p className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">
              信頼度
            </p>
            <p className="text-2xl font-bold text-text-primary">
              {Math.round(musicAnalysis.key_strength * 100)}%
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
