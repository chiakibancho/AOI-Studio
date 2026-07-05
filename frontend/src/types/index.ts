export type VideoType =
  | 'brand'
  | 'corporate'
  | 'recruitment'
  | 'sns_ad'
  | 'youtube'
  | 'short'
  | 'product_pr'

export type ProjectStatus =
  | 'setup'
  | 'music'
  | 'structure'
  | 'storyboard'
  | 'shooting'
  | 'upload'
  | 'export'

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface Project {
  id: string
  title: string
  video_type: VideoType
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

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
