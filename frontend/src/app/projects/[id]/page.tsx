'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import api from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import type { Project, VideoSpec, Structure } from '@/types'
import { VIDEO_TYPE_LABELS, PROJECT_STATUS_LABELS } from '@/types'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import VideoSpecForm from '@/components/project/VideoSpecForm'
import StructureView from '@/components/project/StructureView'

const PHASE_STEPS = [
  { key: 'setup', label: '1. 動画仕様' },
  { key: 'structure', label: '2. AI構成' },
  { key: 'storyboard', label: '3. 絵コンテ' },
  { key: 'shooting', label: '4. 撮影' },
  { key: 'upload', label: '5. 編集' },
  { key: 'export', label: '6. 書き出し' },
]

function getCurrentPhaseIndex(status: string): number {
  const idx = PHASE_STEPS.findIndex((s) => s.key === status)
  return idx >= 0 ? idx : 0
}

export default function ProjectDetailPage() {
  const params = useParams()
  const projectId = params.id as string
  const router = useRouter()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()

  const [generateError, setGenerateError] = useState<string | null>(null)
  const [specSaved, setSpecSaved] = useState(false)

  // Auth guard
  useEffect(() => {
    if (!token) {
      router.replace('/login')
    }
  }, [token, router])

  // Fetch project
  const {
    data: project,
    isLoading: isProjectLoading,
    isError: isProjectError,
  } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const res = await api.get<Project>(`/api/v1/projects/${projectId}`)
      return res.data
    },
    enabled: !!token && !!projectId,
  })

  // Fetch spec (404 → null)
  const { data: spec, isLoading: isSpecLoading } = useQuery<VideoSpec | null>({
    queryKey: ['project-spec', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<VideoSpec>(`/api/v1/projects/${projectId}/spec`)
        return res.data
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: !!token && !!projectId,
  })

  // Fetch structure (404 → null)
  const { data: structure, isLoading: isStructureLoading } = useQuery<Structure | null>({
    queryKey: ['project-structure', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<Structure>(`/api/v1/projects/${projectId}/structure`)
        return res.data
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: !!token && !!projectId,
  })

  // Generate structure mutation
  const generateMutation = useMutation<Structure, Error>({
    mutationFn: async () => {
      const res = await api.post<Structure>(`/api/v1/projects/${projectId}/structure/generate`)
      return res.data
    },
    onSuccess: () => {
      setGenerateError(null)
      queryClient.invalidateQueries({ queryKey: ['project-structure', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setGenerateError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else {
        setGenerateError('構成の生成に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Approve structure mutation
  const approveMutation = useMutation<void, Error>({
    mutationFn: async () => {
      await api.post(`/api/v1/projects/${projectId}/structure/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-structure', projectId] })
    },
  })

  function handleSpecSaved(savedSpec: VideoSpec) {
    queryClient.setQueryData(['project-spec', projectId], savedSpec)
    setSpecSaved(true)
  }

  function handleRegenerate() {
    setGenerateError(null)
    generateMutation.mutate()
  }

  function handleApprove() {
    approveMutation.mutate()
  }

  if (!token) return null

  const isLoading = isProjectLoading || isSpecLoading || isStructureLoading

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.361a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                </svg>
              </div>
              <span className="text-lg font-bold text-text-primary tracking-tight">AOI Studio</span>
            </div>

            <span className="text-border">|</span>

            {/* Back link */}
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              プロジェクト一覧
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 mx-auto w-full max-w-4xl px-4 sm:px-6 lg:px-8 py-10">
        {isLoading && (
          <div className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-4">
              <div className="w-10 h-10 rounded-full border-2 border-accent border-t-transparent animate-spin" />
              <p className="text-sm text-text-secondary">読み込み中...</p>
            </div>
          </div>
        )}

        {isProjectError && !isLoading && (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-text-secondary text-sm">プロジェクトの取得に失敗しました</p>
            </div>
          </div>
        )}

        {!isLoading && project && (
          <div className="flex flex-col gap-8">
            {/* Project title bar */}
            <div className="flex items-start gap-3 flex-wrap">
              <div className="flex-1 min-w-0">
                <h1 className="text-2xl font-bold text-text-primary">{project.title}</h1>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-full bg-surface border border-border text-xs text-text-secondary">
                    {VIDEO_TYPE_LABELS[project.video_type]}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-accent/10 border border-accent/20 text-xs text-accent">
                    {PROJECT_STATUS_LABELS[project.status]}
                  </span>
                </div>
              </div>
            </div>

            {/* Phase stepper */}
            <div className="flex items-center gap-0 overflow-x-auto pb-1">
              {PHASE_STEPS.map((step, index) => {
                const currentIndex = getCurrentPhaseIndex(project.status)
                const isActive = index === currentIndex
                const isDone = index < currentIndex

                return (
                  <div key={step.key} className="flex items-center">
                    <div
                      className={`
                        flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors
                        ${isActive
                          ? 'bg-accent text-white'
                          : isDone
                          ? 'text-text-secondary'
                          : 'text-text-secondary opacity-40'
                        }
                      `}
                    >
                      {isDone && (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      {step.label}
                    </div>
                    {index < PHASE_STEPS.length - 1 && (
                      <svg className="w-4 h-4 text-border flex-shrink-0 mx-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Content area */}
            <div className="flex flex-col gap-6">
              {/* VideoSpec section */}
              {!structure ? (
                <Card>
                  <h2 className="text-base font-semibold text-text-primary mb-6">動画仕様の入力</h2>
                  <VideoSpecForm
                    projectId={projectId}
                    initialSpec={spec ?? null}
                    onSaved={handleSpecSaved}
                  />
                </Card>
              ) : (
                // When structure exists, show spec in collapsed/summary form
                <Card className="opacity-70">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-text-primary">動画仕様</h2>
                    <span className="text-xs text-text-secondary">保存済み</span>
                  </div>
                  {spec && (
                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-text-secondary">
                      <span>{spec.duration_sec}秒</span>
                      <span className="text-border">|</span>
                      <span>{spec.mood}</span>
                      <span className="text-border">|</span>
                      <span className="truncate max-w-xs">{spec.target_audience}</span>
                    </div>
                  )}
                </Card>
              )}

              {/* Generate structure button (spec saved, no structure yet) */}
              {(spec || specSaved) && !structure && (
                <div className="flex flex-col gap-3">
                  {generateError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{generateError}</p>
                    </div>
                  )}
                  <div className="flex justify-center">
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={() => {
                        setGenerateError(null)
                        generateMutation.mutate()
                      }}
                      isLoading={generateMutation.isPending}
                      className="gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.356A3 3 0 0013 18.827V21a1 1 0 01-1 1h-2a1 1 0 01-1-1v-2.173a3 3 0 00-.935-2.17l-.347-.356z" />
                      </svg>
                      AI構成を生成する
                    </Button>
                  </div>
                </div>
              )}

              {/* Structure view */}
              {structure && (
                <div className="flex flex-col gap-3">
                  {generateError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{generateError}</p>
                    </div>
                  )}
                  <Card>
                    <StructureView
                      projectId={projectId}
                      structure={structure}
                      onRegenerate={handleRegenerate}
                      onApprove={handleApprove}
                      isRegenerating={generateMutation.isPending}
                      isApproving={approveMutation.isPending}
                    />
                  </Card>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
