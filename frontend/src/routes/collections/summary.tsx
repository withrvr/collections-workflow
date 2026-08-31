import { createFileRoute, Link } from "@tanstack/react-router"
import { Suspense } from "react"
import { z } from "zod"

import { CollectionsNav } from "@/components/Collections/Nav"
import { SummaryPanel } from "@/components/Collections/SummaryPanel"
import { Skeleton } from "@/components/ui/skeleton"

const searchSchema = z.object({ runId: z.string() })

export const Route = createFileRoute("/collections/summary")({
  component: RouteComponent,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Summary - Collections" }],
  }),
})

function RouteComponent() {
  const { runId } = Route.useSearch()
  return (
    <div className="mx-auto max-w-3xl p-6 md:p-8">
      <CollectionsNav />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">
          Management summary
        </h1>
        <Link
          to="/collections/run-detail"
          search={{ runId }}
          className="text-sm font-medium text-primary hover:underline"
        >
          Back to run
        </Link>
      </div>
      <Suspense fallback={<Skeleton className="h-96 w-full rounded-lg" />}>
        <SummaryPanel runId={runId} />
      </Suspense>
    </div>
  )
}
