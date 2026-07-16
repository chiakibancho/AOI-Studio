'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import api from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import type { Project, VideoSpec, Structure, SpecDraft, SpecFormFields, Storyboard, ShootingList, MusicAnalysis, Character } from '@/types'
import { VIDEO_TYPE_LABELS, PROJECT_STATUS_LABELS } from '@/types'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import VideoSpecForm from '@/components/project/VideoSpecForm'
import StructureView from '@/components/project/StructureView'
import SpecAnalystInput from '@/components/project/SpecAnalystInput'
import SpecDraftView from '@/components/project/SpecDraftView'
import StoryboardView from '@/components/project/StoryboardView'
import ShootingListView from '@/components/project/ShootingListView'
import MusicAnalysisView from '@/components/project/MusicAnalysisView'
import CharacterBibleView from '@/components/project/CharacterBibleView'

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
  const [reviseError, setReviseError] = useState<string | null>(null)
  const [storyboardError, setStoryboardError] = useState<string | null>(null)
  const [storyboardReviseError, setStoryboardReviseError] = useState<string | null>(null)
  const [shootingListError, setShootingListError] = useState<string | null>(null)
  const [musicAnalysisError, setMusicAnalysisError] = useState<string | null>(null)
  const [characterCreateError, setCharacterCreateError] = useState<string | null>(null)
  const [characterActionError, setCharacterActionError] = useState<string | null>(null)
  const [pendingCharacterId, setPendingCharacterId] = useState<string | null>(null)
  const [specSaved, setSpecSaved] = useState(false)
  const [specDraftError, setSpecDraftError] = useState<string | null>(null)
  const [specEntryMode, setSpecEntryMode] = useState<'ai' | 'manual'>('ai')
  const [manualPrefill, setManualPrefill] = useState<SpecFormFields | null>(null)
  const [aiInputSeed, setAiInputSeed] = useState('')
  const [showAiInputOverride, setShowAiInputOverride] = useState(false)

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

  // Fetch spec draft (404 → null). Polls every 2s while analysis is pending.
  // Moot once a real spec exists, so disabled at that point.
  const { data: specDraft } = useQuery<SpecDraft | null>({
    queryKey: ['project-spec-draft', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<SpecDraft>(`/api/v1/projects/${projectId}/spec-draft`)
        return res.data
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: !!token && !!projectId && !spec,
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
  })

  // Generate spec draft mutation
  const generateDraftMutation = useMutation<SpecDraft, Error, string>({
    mutationFn: async (rawInput) => {
      const res = await api.post<SpecDraft>(`/api/v1/projects/${projectId}/spec-draft/generate`, {
        raw_input: rawInput,
      })
      return res.data
    },
    onSuccess: () => {
      setSpecDraftError(null)
      setShowAiInputOverride(false)
      queryClient.invalidateQueries({ queryKey: ['project-spec-draft', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setSpecDraftError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setSpecDraftError('既に生成処理が進行中です。しばらくお待ちください。')
      } else {
        setSpecDraftError('仕様の分析に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Approve spec draft mutation — writes the real VideoSpec
  const approveDraftMutation = useMutation<VideoSpec, Error>({
    mutationFn: async () => {
      const res = await api.post<VideoSpec>(`/api/v1/projects/${projectId}/spec-draft/approve`)
      return res.data
    },
    onSuccess: (savedSpec) => {
      queryClient.setQueryData(['project-spec', projectId], savedSpec)
      setSpecSaved(true)
    },
  })

  // Fetch structure (404 → null). Polls every 2s while generation is pending.
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
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
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
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setGenerateError('既に生成処理が進行中です。しばらくお待ちください。')
      } else {
        setGenerateError('構成の生成に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Approve structure mutation — picks one of the (up to 3) generated options
  const approveMutation = useMutation<void, Error, number>({
    mutationFn: async (optionIndex: number) => {
      await api.post(`/api/v1/projects/${projectId}/structure/approve`, null, {
        params: { option_index: optionIndex },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-structure', projectId] })
    },
  })

  // Revise structure mutation — regenerates a single structure from approved content + feedback
  const reviseMutation = useMutation<Structure, Error, string>({
    mutationFn: async (feedback: string) => {
      const res = await api.post<Structure>(`/api/v1/projects/${projectId}/structure/revise`, {
        feedback,
      })
      return res.data
    },
    onSuccess: () => {
      setReviseError(null)
      queryClient.invalidateQueries({ queryKey: ['project-structure', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setReviseError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setReviseError('既に生成処理が進行中です。しばらくお待ちください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setReviseError('承認済みの構成がありません。先に案を選んで承認してください。')
      } else {
        setReviseError('修正の反映に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Fetch storyboard (404 → null). Polls every 2s while generation is pending.
  // Moot until a Structure has been approved.
  const { data: storyboard, isLoading: isStoryboardLoading } = useQuery<Storyboard | null>({
    queryKey: ['project-storyboard', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<Storyboard>(`/api/v1/projects/${projectId}/storyboard`)
        return res.data
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: !!token && !!projectId && structure?.approved_at != null,
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
  })

  // Generate storyboard mutation
  const generateStoryboardMutation = useMutation<Storyboard, Error>({
    mutationFn: async () => {
      const res = await api.post<Storyboard>(`/api/v1/projects/${projectId}/storyboard/generate`)
      return res.data
    },
    onSuccess: () => {
      setStoryboardError(null)
      queryClient.invalidateQueries({ queryKey: ['project-storyboard', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setStoryboardError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setStoryboardError('既に生成処理が進行中です。しばらくお待ちください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setStoryboardError('承認済みの構成がありません。先に構成案を承認してください。')
      } else {
        setStoryboardError('絵コンテの生成に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Approve storyboard mutation
  const approveStoryboardMutation = useMutation<void, Error>({
    mutationFn: async () => {
      await api.post(`/api/v1/projects/${projectId}/storyboard/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-storyboard', projectId] })
    },
  })

  // Revise storyboard mutation — regenerates a single storyboard from approved content + feedback
  const reviseStoryboardMutation = useMutation<Storyboard, Error, string>({
    mutationFn: async (feedback: string) => {
      const res = await api.post<Storyboard>(`/api/v1/projects/${projectId}/storyboard/revise`, {
        feedback,
      })
      return res.data
    },
    onSuccess: () => {
      setStoryboardReviseError(null)
      queryClient.invalidateQueries({ queryKey: ['project-storyboard', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setStoryboardReviseError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setStoryboardReviseError('既に生成処理が進行中です。しばらくお待ちください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setStoryboardReviseError('承認済みの絵コンテがありません。先に絵コンテを承認してください。')
      } else {
        setStoryboardReviseError('修正の反映に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Fetch shooting list (404 → null). Polls every 2s while generation is pending.
  const { data: shootingList, isLoading: isShootingListLoading } = useQuery<ShootingList | null>({
    queryKey: ['project-shooting-list', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<ShootingList>(`/api/v1/projects/${projectId}/shooting-list`)
        return res.data
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: !!token && !!projectId && storyboard?.approved_at != null,
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
  })

  // Generate shooting list mutation
  const generateShootingListMutation = useMutation<ShootingList, Error>({
    mutationFn: async () => {
      const res = await api.post<ShootingList>(`/api/v1/projects/${projectId}/shooting-list/generate`)
      return res.data
    },
    onSuccess: () => {
      setShootingListError(null)
      queryClient.invalidateQueries({ queryKey: ['project-shooting-list', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setShootingListError('AI APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setShootingListError('既に生成処理が進行中です。しばらくお待ちください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setShootingListError('承認済みの絵コンテがありません。先に絵コンテを承認してください。')
      } else {
        setShootingListError('撮影リストの生成に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Approve shooting list mutation
  const approveShootingListMutation = useMutation<void, Error>({
    mutationFn: async () => {
      await api.post(`/api/v1/projects/${projectId}/shooting-list/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-shooting-list', projectId] })
    },
  })

  // Toggle a shot's completed flag
  const toggleShotMutation = useMutation<ShootingList, Error, { cutNumber: number; completed: boolean }>({
    mutationFn: async ({ cutNumber, completed }) => {
      const res = await api.patch<ShootingList>(
        `/api/v1/projects/${projectId}/shooting-list/shots/${cutNumber}`,
        { completed }
      )
      return res.data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['project-shooting-list', projectId], data)
    },
  })

  // Fetch music analysis (404 → null)
  const { data: musicAnalysis } = useQuery<MusicAnalysis | null>({
    queryKey: ['project-music-analysis', projectId],
    queryFn: async () => {
      try {
        const res = await api.get<MusicAnalysis>(`/api/v1/projects/${projectId}/music-analysis`)
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

  // Upload & analyze BGM
  const uploadMusicMutation = useMutation<MusicAnalysis, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post<MusicAnalysis>(
        `/api/v1/projects/${projectId}/music-analysis`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      return res.data
    },
    onSuccess: (data) => {
      setMusicAnalysisError(null)
      queryClient.setQueryData(['project-music-analysis', projectId], data)
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 422) {
        setMusicAnalysisError('非対応の音声フォーマットです。mp3またはwavファイルをアップロードしてください。')
      } else {
        setMusicAnalysisError('BGM解析に失敗しました。もう一度お試しください。')
      }
    },
  })

  function handleUploadMusic(file: File) {
    setMusicAnalysisError(null)
    uploadMusicMutation.mutate(file)
  }

  // Fetch character bible template variables (project-independent, static)
  const { data: templateVariables } = useQuery<string[]>({
    queryKey: ['character-template-variables'],
    queryFn: async () => {
      const res = await api.get<{ template_version: string; variables: string[] }>(
        '/api/v1/characters/template-variables'
      )
      return res.data.variables
    },
    enabled: !!token,
    staleTime: Infinity,
  })

  // Fetch characters for this project. Polls every 2s while any character is generating.
  const { data: characters } = useQuery<Character[]>({
    queryKey: ['project-characters', projectId],
    queryFn: async () => {
      const res = await api.get<Character[]>(`/api/v1/projects/${projectId}/characters`)
      return res.data
    },
    enabled: !!token && !!projectId,
    refetchInterval: (query) =>
      query.state.data?.some((c) => c.status === 'generating') ? 2000 : false,
  })

  // Create character mutation
  const createCharacterMutation = useMutation<Character, Error, { name: string; variables: Record<string, string> }>({
    mutationFn: async ({ name, variables }) => {
      const res = await api.post<Character>(`/api/v1/projects/${projectId}/characters`, {
        name,
        variables,
      })
      return res.data
    },
    onSuccess: () => {
      setCharacterCreateError(null)
      queryClient.invalidateQueries({ queryKey: ['project-characters', projectId] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 422) {
        setCharacterCreateError('入力内容がテンプレートの項目と一致しません。')
      } else {
        setCharacterCreateError('キャラクターの作成に失敗しました。もう一度お試しください。')
      }
    },
  })

  // Generate character sheet mutation
  const generateCharacterMutation = useMutation<Character, Error, string>({
    mutationFn: async (characterId) => {
      const res = await api.post<Character>(`/api/v1/characters/${characterId}/generate`)
      return res.data
    },
    onSuccess: () => {
      setCharacterActionError(null)
      queryClient.invalidateQueries({ queryKey: ['project-characters', projectId] })
    },
    onError: (err) => {
      setPendingCharacterId(null)
      if (axios.isAxiosError(err) && err.response?.status === 503) {
        setCharacterActionError('AI画像生成APIキーが設定されていません。管理者にお問い合わせください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 409) {
        setCharacterActionError('既に生成処理が進行中です。しばらくお待ちください。')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setCharacterActionError('承認済みのキャラクターは再生成できません。')
      } else {
        setCharacterActionError('モデルシートの生成に失敗しました。もう一度お試しください。')
      }
    },
    onSettled: () => {
      setPendingCharacterId(null)
    },
  })

  // Approve character mutation
  const approveCharacterMutation = useMutation<Character, Error, string>({
    mutationFn: async (characterId) => {
      const res = await api.post<Character>(`/api/v1/characters/${characterId}/approve`)
      return res.data
    },
    onSuccess: () => {
      setCharacterActionError(null)
      queryClient.invalidateQueries({ queryKey: ['project-characters', projectId] })
    },
    onError: () => {
      setCharacterActionError('承認に失敗しました。もう一度お試しください。')
    },
    onSettled: () => {
      setPendingCharacterId(null)
    },
  })

  function handleCreateCharacter(name: string, variables: Record<string, string>) {
    setCharacterCreateError(null)
    createCharacterMutation.mutate({ name, variables })
  }

  function handleGenerateCharacter(characterId: string) {
    setCharacterActionError(null)
    setPendingCharacterId(characterId)
    generateCharacterMutation.mutate(characterId)
  }

  function handleApproveCharacter(characterId: string) {
    setCharacterActionError(null)
    setPendingCharacterId(characterId)
    approveCharacterMutation.mutate(characterId)
  }

  function handleSpecSaved(savedSpec: VideoSpec) {
    queryClient.setQueryData(['project-spec', projectId], savedSpec)
    setSpecSaved(true)
  }

  function handleGenerateDraft(rawInput: string) {
    setSpecDraftError(null)
    generateDraftMutation.mutate(rawInput)
  }

  function handleApproveDraft() {
    approveDraftMutation.mutate()
  }

  function handleEditManually(prefill: SpecFormFields | null) {
    setManualPrefill(prefill)
    setSpecEntryMode('manual')
  }

  function handleRestartAiInput(rawInputSeed: string) {
    setAiInputSeed(rawInputSeed)
    setShowAiInputOverride(true)
  }

  function handleRegenerate() {
    setGenerateError(null)
    generateMutation.mutate()
  }

  function handleApprove(optionIndex: number) {
    approveMutation.mutate(optionIndex)
  }

  function handleRevise(feedback: string) {
    setReviseError(null)
    reviseMutation.mutate(feedback)
  }

  function handleGenerateStoryboard() {
    setStoryboardError(null)
    generateStoryboardMutation.mutate()
  }

  function handleApproveStoryboard() {
    approveStoryboardMutation.mutate()
  }

  function handleReviseStoryboard(feedback: string) {
    setStoryboardReviseError(null)
    reviseStoryboardMutation.mutate(feedback)
  }

  function handleGenerateShootingList() {
    setShootingListError(null)
    generateShootingListMutation.mutate()
  }

  function handleApproveShootingList() {
    approveShootingListMutation.mutate()
  }

  function handleToggleShot(cutNumber: number, completed: boolean) {
    toggleShotMutation.mutate({ cutNumber, completed })
  }

  function handleDownloadCsv() {
    if (!project) return
    api
      .get(`/api/v1/projects/${projectId}/shooting-list/export`, { responseType: 'blob' })
      .then((res) => {
        const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
        const today = new Date()
        const yyyy = today.getFullYear()
        const mm = String(today.getMonth() + 1).padStart(2, '0')
        const dd = String(today.getDate()).padStart(2, '0')
        const filename = `${project.title}_撮影リスト_${yyyy}${mm}${dd}.csv`

        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      })
      .catch((error) => {
        console.error('CSVダウンロードに失敗しました', error)
      })
  }

  if (!token) return null

  const isLoading =
    isProjectLoading || isSpecLoading || isStructureLoading || isStoryboardLoading || isShootingListLoading

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

            {/* Character Bible (独立機能: フェーズゲーティングの対象外で常に表示) */}
            <Card>
              <CharacterBibleView
                characters={characters ?? []}
                templateVariables={templateVariables ?? []}
                onCreate={handleCreateCharacter}
                onGenerate={handleGenerateCharacter}
                onApprove={handleApproveCharacter}
                isCreating={createCharacterMutation.isPending}
                createError={characterCreateError}
                actionError={characterActionError}
                pendingCharacterId={pendingCharacterId}
              />
            </Card>

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
                spec || specEntryMode === 'manual' ? (
                  <Card>
                    <h2 className="text-base font-semibold text-text-primary mb-6">動画仕様の入力</h2>
                    <VideoSpecForm
                      projectId={projectId}
                      initialSpec={spec ?? manualPrefill}
                      onSaved={handleSpecSaved}
                    />
                  </Card>
                ) : (
                  <Card>
                    <h2 className="text-base font-semibold text-text-primary mb-2">動画仕様をAIに相談する</h2>
                    <p className="text-sm text-text-secondary mb-6">
                      作りたい動画のイメージを自由に書いてください。AIが仕様として整理します。
                    </p>
                    {specDraft && !showAiInputOverride ? (
                      <SpecDraftView
                        draft={specDraft}
                        onApprove={handleApproveDraft}
                        onEditManually={() =>
                          handleEditManually({
                            duration_sec: specDraft.duration_sec,
                            target_audience: specDraft.target_audience,
                            message: specDraft.message,
                            mood: specDraft.mood,
                            style_notes: specDraft.style_notes,
                            reference_urls: specDraft.reference_urls,
                          })
                        }
                        onRestart={handleRestartAiInput}
                        isApproving={approveDraftMutation.isPending}
                      />
                    ) : (
                      <SpecAnalystInput
                        initialValue={aiInputSeed}
                        onSubmit={handleGenerateDraft}
                        isSubmitting={generateDraftMutation.isPending}
                        error={specDraftError}
                        onManualEntry={() => handleEditManually(null)}
                      />
                    )}
                  </Card>
                )
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
                      onRevise={handleRevise}
                      isRegenerating={generateMutation.isPending || structure.status === 'pending'}
                      isApproving={approveMutation.isPending}
                      isRevising={reviseMutation.isPending || structure.status === 'pending'}
                      reviseError={reviseError}
                    />
                  </Card>
                </div>
              )}

              {/* Generate storyboard button (structure approved, no storyboard yet) */}
              {structure?.approved_at != null && !storyboard && (
                <div className="flex flex-col gap-3">
                  {storyboardError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{storyboardError}</p>
                    </div>
                  )}
                  <div className="flex justify-center">
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={handleGenerateStoryboard}
                      isLoading={generateStoryboardMutation.isPending}
                      className="gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.356A3 3 0 0013 18.827V21a1 1 0 01-1 1h-2a1 1 0 01-1-1v-2.173a3 3 0 00-.935-2.17l-.347-.356z" />
                      </svg>
                      絵コンテを生成する
                    </Button>
                  </div>
                </div>
              )}

              {/* Storyboard view */}
              {structure && storyboard && (
                <div className="flex flex-col gap-3">
                  {storyboardError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{storyboardError}</p>
                    </div>
                  )}
                  <Card>
                    <StoryboardView
                      projectId={projectId}
                      storyboard={storyboard}
                      structure={structure}
                      onRegenerate={handleGenerateStoryboard}
                      onApprove={handleApproveStoryboard}
                      onRevise={handleReviseStoryboard}
                      isRegenerating={generateStoryboardMutation.isPending || storyboard.status === 'pending'}
                      isApproving={approveStoryboardMutation.isPending}
                      isRevising={reviseStoryboardMutation.isPending || storyboard.status === 'pending'}
                      reviseError={storyboardReviseError}
                    />
                  </Card>
                </div>
              )}

              {/* Generate shooting list button (storyboard approved, no shooting list yet) */}
              {storyboard?.approved_at != null && !shootingList && (
                <div className="flex flex-col gap-3">
                  {shootingListError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{shootingListError}</p>
                    </div>
                  )}
                  <div className="flex justify-center">
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={handleGenerateShootingList}
                      isLoading={generateShootingListMutation.isPending}
                      className="gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                      撮影リストを作成する
                    </Button>
                  </div>
                </div>
              )}

              {/* BGM analysis */}
              {storyboard && shootingList && (
                <Card>
                  <MusicAnalysisView
                    musicAnalysis={musicAnalysis ?? null}
                    onUpload={handleUploadMusic}
                    isUploading={uploadMusicMutation.isPending}
                    error={musicAnalysisError}
                  />
                </Card>
              )}

              {/* Shooting list view */}
              {storyboard && shootingList && (
                <div className="flex flex-col gap-3">
                  {shootingListError && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3">
                      <p className="text-sm text-red-400">{shootingListError}</p>
                    </div>
                  )}
                  <Card>
                    <ShootingListView
                      projectId={projectId}
                      shootingList={shootingList}
                      onRegenerate={handleGenerateShootingList}
                      onApprove={handleApproveShootingList}
                      onToggleShot={handleToggleShot}
                      onDownloadCsv={handleDownloadCsv}
                      isRegenerating={generateShootingListMutation.isPending || shootingList.status === 'pending'}
                      isApproving={approveShootingListMutation.isPending}
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
