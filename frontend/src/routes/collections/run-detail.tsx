import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
} from "lucide-react"
import { Suspense, useState } from "react"
import { z } from "zod"

import { CollectionsService, type RunEventOut } from "@/client"
import { ExceptionsPanel } from "@/components/Collections/ExceptionsPanel"
import { CollectionsNav } from "@/components/Collections/Nav"
import { StatusBadge } from "@/components/Collections/StatusBadge"
import { SummaryPanel } from "@/components/Collections/SummaryPanel"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const searchSchema = z.object({ runId: z.string() })

export const Route = createFileRoute("/collections/run-detail")({
  component: RouteComponent,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Run detail - Collections" }],
  }),
})

const STAGE_LABELS: Record<string, string> = {
  load: "Load workbook",
  validate: "Validate & explain exceptions",
  calculate: "Calculate outstanding & overdue",
  control: "Control gate",
  summarise: "Summarise",
  persist: "Persist results",
}

function groupByStage(events: RunEventOut[]) {
  const groups: { stage: string; events: RunEventOut[] }[] = []
  for (const event of events) {
    const last = groups[groups.length - 1]
    if (last && last.stage === event.stage) {
      last.events.push(event)
    } else {
      groups.push({ stage: event.stage, events: [event] })
    }
  }
  return groups
}

function StageIcon({ events }: { events: RunEventOut[] }) {
  if (events.some((e) => e.level === "error")) {
    return <AlertCircle className="size-5 text-destructive" />
  }
  if (events.some((e) => e.level === "warning")) {
    return <AlertCircle className="size-5 text-amber-500" />
  }
  return <CheckCircle2 className="size-5 text-green-600" />
}

function StageStep({
  stage,
  events,
}: {
  stage: string
  events: RunEventOut[]
}) {
  const [open, setOpen] = useState(false)
  return (
    <li className="relative pl-8">
      <span className="absolute left-0 top-0.5">
        <StageIcon events={events} />
      </span>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="font-medium">
          {STAGE_LABELS[stage] ?? stage}
          <span className="ml-2 text-xs text-muted-foreground">
            {events.length} event{events.length === 1 ? "" : "s"}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "size-4 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <ul className="mt-2 space-y-2 border-l pl-4">
          {events.map((event) => (
            <li key={event.id} className="text-sm">
              <div className="flex items-center gap-2">
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                  {event.code}
                </code>
                <span className="text-xs text-muted-foreground">
                  {new Date(event.ts).toLocaleTimeString()}
                </span>
              </div>
              <p
                className={cn(
                  "mt-0.5",
                  event.level === "error" && "text-destructive",
                  event.level === "warning" && "text-amber-600",
                )}
              >
                {event.message}
              </p>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

function Timeline({ runId }: { runId: string }) {
  const { data: eventsResponse } = useSuspenseQuery({
    queryFn: async () =>
      (await CollectionsService.getRunEvents({ path: { run_id: runId } })).data,
    queryKey: ["collections", "run", runId, "events"],
  })
  const stages = groupByStage(eventsResponse?.data ?? [])

  if (stages.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <CircleDashed className="size-4" /> No events yet.
      </p>
    )
  }

  return (
    <ol className="space-y-4">
      {stages.map((group, i) => (
        <StageStep key={`${group.stage}-${i}`} {...group} />
      ))}
    </ol>
  )
}

function RunDetailContent({ runId }: { runId: string }) {
  const { data: run } = useSuspenseQuery({
    queryFn: async () =>
      (await CollectionsService.getRun({ path: { run_id: runId } })).data,
    queryKey: ["collections", "run", runId],
  })

  if (!run) return null
  const finished = run.status === "PASSED" || run.status === "BLOCKED"

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {run.source_filename}
          </h1>
          <p className="text-muted-foreground">
            Report date {run.report_date} · created{" "}
            {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
        <StatusBadge status={run.status} />
      </div>

      {run.status === "FAILED" && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>{run.error_code}</AlertTitle>
          <AlertDescription>{run.error_message}</AlertDescription>
        </Alert>
      )}

      <div>
        <h2 className="mb-3 text-lg font-semibold">Timeline</h2>
        <Suspense fallback={<Skeleton className="h-40 w-full rounded-lg" />}>
          <Timeline runId={runId} />
        </Suspense>
      </div>

      {finished && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Summary</h2>
            <Link
              to="/collections/summary"
              search={{ runId: run.id }}
              className="text-sm font-medium text-primary hover:underline"
            >
              Open full page
            </Link>
          </div>
          <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg" />}>
            <SummaryPanel runId={runId} />
          </Suspense>
        </div>
      )}

      {finished && (run.exception_count ?? 0) > 0 && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Exceptions ({run.exception_count})
            </h2>
            <Link
              to="/collections/exceptions"
              search={{ runId: run.id }}
              className="text-sm font-medium text-primary hover:underline"
            >
              Open full page with filters
            </Link>
          </div>
          <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg" />}>
            <ExceptionsPanel runId={runId} limit={10} />
          </Suspense>
        </div>
      )}
    </div>
  )
}

function RouteComponent() {
  const { runId } = Route.useSearch()
  return (
    <div className="mx-auto max-w-4xl p-6 md:p-8">
      <CollectionsNav />
      <Suspense fallback={<Skeleton className="h-96 w-full rounded-lg" />}>
        <RunDetailContent runId={runId} />
      </Suspense>
    </div>
  )
}
