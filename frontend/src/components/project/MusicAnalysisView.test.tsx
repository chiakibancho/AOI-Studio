import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MusicAnalysisView from './MusicAnalysisView'
import type { MusicAnalysis } from '@/types'

const baseAnalysis: MusicAnalysis = {
  id: 'ma1',
  project_id: 'p1',
  filename: 'bgm.wav',
  bpm: 120.4,
  key: 'A',
  scale: 'minor',
  key_strength: 0.72,
  analyzed_at: '2026-07-16T00:00:00Z',
}

function renderView(
  props: Partial<React.ComponentProps<typeof MusicAnalysisView>> = {}
) {
  return render(
    <MusicAnalysisView
      musicAnalysis={null}
      onUpload={vi.fn()}
      isUploading={false}
      error={null}
      {...props}
    />
  )
}

describe('MusicAnalysisView', () => {
  it('disables the analyze button until a file is selected', () => {
    renderView()

    const button = screen.getByRole('button', { name: '解析する' })
    expect(button).toBeDisabled()

    const input = screen.getByLabelText('BGMファイルを選択') as HTMLInputElement
    const file = new File(['dummy'], 'bgm.wav', { type: 'audio/wav' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(button).not.toBeDisabled()
  })

  it('calls onUpload with the selected file when clicked', () => {
    const onUpload = vi.fn()
    renderView({ onUpload })

    const input = screen.getByLabelText('BGMファイルを選択') as HTMLInputElement
    const file = new File(['dummy'], 'bgm.wav', { type: 'audio/wav' })
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '解析する' }))

    expect(onUpload).toHaveBeenCalledWith(file)
  })

  it('shows the error message when analysis fails', () => {
    renderView({ error: '非対応の音声フォーマットです。mp3またはwavファイルをアップロードしてください。' })

    expect(
      screen.getByText('非対応の音声フォーマットです。mp3またはwavファイルをアップロードしてください。')
    ).toBeInTheDocument()
  })

  it('shows BPM, key, and confidence once analysis is available', () => {
    renderView({ musicAnalysis: baseAnalysis })

    expect(screen.getByText('bgm.wav')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText('A マイナー')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
  })
})
