import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ShootingListView from './ShootingListView'
import type { ShootingList, ShotImage } from '@/types'

const NOT_FOUND_ERROR = { isAxiosError: true, response: { status: 404 }, message: 'Not Found' }

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(() => Promise.reject(NOT_FOUND_ERROR)),
    post: vi.fn(),
  },
}))

import api from '@/lib/api'

const mockedApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> }

const baseShootingList: ShootingList = {
  id: 'sl1',
  project_id: 'p1',
  storyboard_id: 'sb1',
  shots: [
    {
      cut_number: 1,
      scene_number: 1,
      category: 'people',
      title: 'オフィス入口での挨拶ショット',
      location: 'オフィスエントランス',
      equipment: '一眼カメラ、ジンバル',
      talent_props: '出演者A',
      notes: '逆光に注意',
      completed: false,
    },
    {
      cut_number: 2,
      scene_number: 1,
      category: 'people',
      title: 'クローズアップ',
      location: 'オフィスエントランス',
      equipment: '一眼カメラ',
      talent_props: '出演者A',
      notes: '',
      completed: false,
    },
    {
      cut_number: 3,
      scene_number: 2,
      category: 'product',
      title: '商品カット',
      location: '会議室',
      equipment: '三脚',
      talent_props: '製品サンプル',
      notes: '',
      completed: true,
    },
  ],
  version: 1,
  status: 'completed',
  error_message: null,
  approved_at: null,
  generated_at: '2026-07-15T00:00:00Z',
}

function renderView(
  overrides: Partial<ShootingList> = {},
  handlers: {
    onApprove?: () => void
    onToggleShot?: (cutNumber: number, completed: boolean) => void
    onDownloadCsv?: () => void
  } = {}
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ShootingListView
        projectId="p1"
        shootingList={{ ...baseShootingList, ...overrides }}
        onRegenerate={vi.fn()}
        onApprove={handlers.onApprove ?? vi.fn()}
        onToggleShot={handlers.onToggleShot ?? vi.fn()}
        onDownloadCsv={handlers.onDownloadCsv ?? vi.fn()}
        isRegenerating={false}
        isApproving={false}
      />
    </QueryClientProvider>
  )
}

describe('ShootingListView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.get.mockImplementation(() => Promise.reject(NOT_FOUND_ERROR))
  })

  it('shows a loading state and no shots while pending', () => {
    renderView({ status: 'pending', shots: [] })

    expect(screen.getByText('AIが撮影リストを生成しています...')).toBeInTheDocument()
    expect(screen.queryByText('商品カット')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'CSVダウンロード' })).toBeDisabled()
  })

  it('enables the CSV download button when shots exist and calls the handler on click', () => {
    const onDownloadCsv = vi.fn()
    renderView({}, { onDownloadCsv })

    const button = screen.getByRole('button', { name: 'CSVダウンロード' })
    expect(button).not.toBeDisabled()
    fireEvent.click(button)
    expect(onDownloadCsv).toHaveBeenCalled()
  })

  it('keeps the CSV download button visible after approval', () => {
    renderView({ approved_at: '2026-07-15T01:00:00Z' })

    expect(screen.getByRole('button', { name: 'CSVダウンロード' })).not.toBeDisabled()
  })

  it('shows the error message when failed', () => {
    renderView({ status: 'failed', shots: [], error_message: 'Claude API エラー: 401' })

    expect(screen.getByText(/撮影リストの生成に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/Claude API エラー: 401/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再生成する' })).not.toBeDisabled()
  })

  it('groups shots by category and shows the completion count', () => {
    renderView()

    expect(screen.getByText('人物')).toBeInTheDocument()
    expect(screen.getByText('商品')).toBeInTheDocument()
    expect(screen.getByText('オフィス入口での挨拶ショット')).toBeInTheDocument()
    expect(screen.getByText('クローズアップ')).toBeInTheDocument()
    expect(screen.getByText('商品カット')).toBeInTheDocument()
    expect(screen.getByText('1/3 完了')).toBeInTheDocument()
  })

  it('calls onToggleShot with the cut_number and new completed value', () => {
    const onToggleShot = vi.fn()
    renderView({}, { onToggleShot })

    const checkbox = screen.getByLabelText('カット1を撮影完了にする')
    fireEvent.click(checkbox)

    expect(onToggleShot).toHaveBeenCalledWith(1, true)
  })

  it('shows an approve button when completed and not yet approved', () => {
    const onApprove = vi.fn()
    renderView({}, { onApprove })

    fireEvent.click(screen.getByRole('button', { name: 'この撮影リストで進む' }))
    expect(onApprove).toHaveBeenCalled()
  })

  it('hides the approve/regenerate buttons and shows a badge once approved, but keeps checkboxes usable', () => {
    const onToggleShot = vi.fn()
    renderView({ approved_at: '2026-07-15T01:00:00Z' }, { onToggleShot })

    expect(screen.getByText('承認済み')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'この撮影リストで進む' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '再生成する' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('カット1を撮影完了にする'))
    expect(onToggleShot).toHaveBeenCalledWith(1, true)
  })
})

describe('ShootingListView shot image generation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.get.mockImplementation(() => Promise.reject(NOT_FOUND_ERROR))
  })

  it('renders a generate button and a collapsed Style toggle for each shot', () => {
    renderView()

    const generateButtons = screen.getAllByRole('button', { name: '絵コンテ生成' })
    expect(generateButtons).toHaveLength(3)
    expect(screen.getAllByText(/Style/).length).toBeGreaterThan(0)
    expect(screen.queryByLabelText('Style')).not.toBeInTheDocument()
  })

  it('expands the Style section to reveal preset and custom options', () => {
    renderView({ shots: [baseShootingList.shots[0]] })

    fireEvent.click(screen.getByText(/Style ▼/))

    const select = screen.getByLabelText('Style') as HTMLSelectElement
    expect(select).toBeInTheDocument()
    expect(select.value).toBe('cinematic realism, Sony FX3 aesthetic')

    fireEvent.change(select, { target: { value: 'custom' } })
    expect(screen.getByLabelText('カスタムStyle')).toBeInTheDocument()
  })

  it('calls generate-image with the selected style preset', async () => {
    mockedApi.post.mockResolvedValue({
      data: {
        id: 'si1',
        project_id: 'p1',
        shooting_list_id: 'sl1',
        cut_number: 1,
        image_path: null,
        status: 'generating',
        error_message: null,
        created_at: '2026-07-15T00:00:00Z',
        updated_at: '2026-07-15T00:00:00Z',
      } satisfies ShotImage,
    })
    renderView({ shots: [baseShootingList.shots[0]] })

    fireEvent.click(screen.getByRole('button', { name: '絵コンテ生成' }))

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        '/api/v1/projects/p1/shooting-list/shots/1/generate-image',
        { style: 'cinematic realism, Sony FX3 aesthetic' }
      )
    })
  })

  it('shows a thumbnail once the shot image has generated', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.endsWith('/image-status')) {
        return Promise.resolve({
          data: {
            id: 'si1',
            project_id: 'p1',
            shooting_list_id: 'sl1',
            cut_number: 1,
            image_path: 'shot_images/si1.png',
            status: 'generated',
            error_message: null,
            created_at: '2026-07-15T00:00:00Z',
            updated_at: '2026-07-15T00:00:00Z',
          } satisfies ShotImage,
        })
      }
      if (url.endsWith('/image')) {
        return Promise.resolve({ data: new Blob(['fake'], { type: 'image/png' }) })
      }
      return Promise.reject(NOT_FOUND_ERROR)
    })

    renderView({ shots: [baseShootingList.shots[0]] })

    expect(
      await screen.findByAltText('カット1の絵コンテイラスト')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '絵コンテ再生成' })).toBeInTheDocument()
  })

  it('shows the error message when generation failed', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url.endsWith('/image-status')) {
        return Promise.resolve({
          data: {
            id: 'si1',
            project_id: 'p1',
            shooting_list_id: 'sl1',
            cut_number: 1,
            image_path: null,
            status: 'failed',
            error_message: 'Together AI エラー: 500',
            created_at: '2026-07-15T00:00:00Z',
            updated_at: '2026-07-15T00:00:00Z',
          } satisfies ShotImage,
        })
      }
      return Promise.reject(NOT_FOUND_ERROR)
    })

    renderView({ shots: [baseShootingList.shots[0]] })

    expect(await screen.findByText('Together AI エラー: 500')).toBeInTheDocument()
  })
})
