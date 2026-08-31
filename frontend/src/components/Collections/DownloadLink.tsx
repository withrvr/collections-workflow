import { Download } from "lucide-react"

/** Plain native download link -- no JS needed, the backend serves this
 * origin so a relative href just works (single-port serving, see
 * ARCHITECTURE.md). `has_download` is false for runs created before this
 * feature shipped, or if the file was never persisted. */
export function DownloadLink({
  runId,
  hasDownload,
  label = "Download original file",
}: {
  runId: string
  hasDownload: boolean
  label?: string
}) {
  if (!hasDownload) return null
  return (
    <a
      href={`/api/v1/collections/runs/${runId}/download`}
      download
      title="Download the exact file that was uploaded for this run"
      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
    >
      <Download className="size-3.5" /> {label}
    </a>
  )
}
