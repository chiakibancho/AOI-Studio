import Link from 'next/link'
import type { Project } from '@/types'
import { VIDEO_TYPE_LABELS, PROJECT_STATUS_LABELS } from '@/types'
import Card from '@/components/ui/Card'

interface ProjectCardProps {
  project: Project
}

const STATUS_COLORS: Record<string, string> = {
  setup: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  music: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  structure: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  storyboard: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  shooting: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
  upload: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  export: 'bg-green-500/20 text-green-300 border-green-500/30',
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

export default function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`} className="block">
      <Card hoverable className="h-full flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-text-primary font-semibold text-base leading-snug line-clamp-2">
            {project.title}
          </h3>
          <span className="shrink-0 rounded-full bg-accent/15 border border-accent/30 px-2.5 py-0.5 text-xs font-medium text-accent">
            {VIDEO_TYPE_LABELS[project.video_type]}
          </span>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[project.status]}`}
          >
            <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
            {PROJECT_STATUS_LABELS[project.status]}
          </span>
        </div>

        {/* Footer */}
        <div className="mt-auto pt-2 border-t border-border">
          <p className="text-xs text-text-secondary">
            作成日: {formatDate(project.created_at)}
          </p>
        </div>
      </Card>
    </Link>
  )
}
