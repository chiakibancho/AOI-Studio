import type { components } from './api-generated'

export type VideoType = components['schemas']['VideoType']
export type ProjectStatus = components['schemas']['ProjectStatus']
export type StructureStatus = components['schemas']['StructureStatus']
export type SpecDraftStatus = components['schemas']['SpecDraftStatus']
export type StoryboardStatus = components['schemas']['StoryboardStatus']
export type ShootingListStatus = components['schemas']['ShootingListStatus']

export type User = components['schemas']['UserResponse']
export type Project = components['schemas']['ProjectResponse']
export type VideoSpec = components['schemas']['VideoSpecResponse']
export type SceneItem = components['schemas']['SceneItem']
export type StructureOption = components['schemas']['StructureOption']
export type Structure = components['schemas']['StructureResponse']
export type SpecDraft = components['schemas']['SpecDraftResponse']
export type StoryboardScene = components['schemas']['StoryboardScene']
export type Storyboard = components['schemas']['StoryboardResponse']
export type ShootingListShot = components['schemas']['ShootingListShot']
export type ShotCategory = ShootingListShot['category']
export type ShootingList = components['schemas']['ShootingListResponse']
export type MusicAnalysis = components['schemas']['MusicAnalysisResponse']
export type AuthResponse = components['schemas']['TokenResponse']

export type SpecFormFields = Pick<
  VideoSpec,
  'duration_sec' | 'target_audience' | 'message' | 'mood' | 'style_notes' | 'reference_urls'
>

export const VIDEO_TYPE_LABELS: Record<VideoType, string> = {
  brand: 'ブランド動画',
  corporate: '企業紹介',
  recruitment: '採用動画',
  sns_ad: 'SNS広告',
  youtube: 'YouTube',
  short: 'ショート動画',
  product_pr: '商品PR',
}

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  setup: '企画中',
  music: '音楽設定',
  structure: '構成作成',
  storyboard: '絵コンテ',
  shooting: '撮影',
  upload: 'アップロード',
  export: 'エクスポート',
}

export const SHOT_CATEGORY_LABELS: Record<ShotCategory, string> = {
  exterior: '外観',
  people: '人物',
  product: '商品',
  broll: 'Bロール',
  other: 'その他',
}

export const SHOT_CATEGORY_ORDER: ShotCategory[] = ['exterior', 'people', 'product', 'broll', 'other']

export const MOOD_OPTIONS = [
  { value: 'professional', label: 'プロフェッショナル' },
  { value: 'casual', label: 'カジュアル' },
  { value: 'emotional', label: '感動的' },
  { value: 'energetic', label: 'エネルギッシュ' },
  { value: 'luxury', label: '高級感' },
  { value: 'friendly', label: '親しみやすい' },
  { value: 'serious', label: 'シリアス' },
  { value: 'playful', label: 'ポップ・遊び心' },
] as const
