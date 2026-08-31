import { createFileRoute, Link } from "@tanstack/react-router"
import { Suspense } from "react"
import { z } from "zod"
import { ExceptionsPanel } from "@/components/Collections/ExceptionsPanel"
import { CollectionsNav } from "@/components/Collections/Nav"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"

const searchSchema = z.object({
  runId: z.string(),
  ruleCode: z.string().optional(),
  severity: z.string().optional(),
})

export const Route = createFileRoute("/collections/exceptions")({
  component: RouteComponent,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Exceptions - Collections" }],
  }),
})

function RouteComponent() {
  const { runId, ruleCode, severity } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="mx-auto max-w-5xl p-6 md:p-8">
      <CollectionsNav />
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Exceptions</h1>
          <p className="text-muted-foreground">
            Every data-quality or business-rule issue this run found, with
            cause, impact, suggested fix, and owner.
          </p>
        </div>
        <Link
          to="/collections/run-detail"
          search={{ runId }}
          className="text-sm font-medium text-primary hover:underline"
        >
          Back to run
        </Link>
      </div>

      <div className="mb-4 flex gap-3">
        <Select
          value={severity ?? "all"}
          onValueChange={(value) =>
            navigate({
              search: (prev) => ({
                ...prev,
                severity: value === "all" ? undefined : value,
              }),
            })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg" />}>
        <ExceptionsPanel
          runId={runId}
          ruleCode={ruleCode}
          severity={severity}
        />
      </Suspense>
    </div>
  )
}
