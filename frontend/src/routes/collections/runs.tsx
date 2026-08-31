import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, FileQuestion } from "lucide-react"
import { Suspense } from "react"
import { z } from "zod"

import { CollectionsService } from "@/client"
import { DownloadLink } from "@/components/Collections/DownloadLink"
import { CollectionsNav } from "@/components/Collections/Nav"
import { StatusBadge } from "@/components/Collections/StatusBadge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const PAGE_SIZE = 20

const searchSchema = z.object({ page: z.number().int().min(0).catch(0) })

export const Route = createFileRoute("/collections/runs")({
  component: RouteComponent,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Runs - Collections" }],
  }),
})

function formatMoney(value: string | null) {
  if (value === null) return "—"
  return `Rs ${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function RunsTable({ page }: { page: number }) {
  const navigate = useNavigate({ from: "/collections/runs" })
  const { data } = useSuspenseQuery({
    queryFn: async () =>
      (
        await CollectionsService.listRuns({
          query: { skip: page * PAGE_SIZE, limit: PAGE_SIZE },
        })
      ).data,
    queryKey: ["collections", "runs", page],
  })

  if (data.data.length === 0 && page === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-16 text-center">
        <FileQuestion className="size-8 text-muted-foreground" />
        <div>
          <p className="font-medium">No runs yet</p>
          <p className="text-sm text-muted-foreground">
            Upload a workbook to create the first one.
          </p>
        </div>
      </div>
    )
  }

  const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE))

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Overdue</TableHead>
              <TableHead className="text-right">Outstanding</TableHead>
              <TableHead className="text-right">Exceptions</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.data.map((run) => (
              <TableRow key={run.id} className="hover:bg-muted/50">
                <TableCell>
                  <Link
                    to="/collections/run-detail"
                    search={{ runId: run.id }}
                    className="font-medium text-primary hover:underline"
                    title={run.source_filename}
                  >
                    {run.source_filename}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={run.status} />
                </TableCell>
                <TableCell
                  className="text-muted-foreground"
                  title={new Date(run.created_at).toISOString()}
                >
                  {new Date(run.created_at).toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {run.overdue_count ?? "—"}
                </TableCell>
                <TableCell
                  className="text-right"
                  title={run.total_outstanding ?? undefined}
                >
                  {formatMoney(run.total_outstanding)}
                </TableCell>
                <TableCell className="text-right">
                  {run.exception_count ?? "—"}
                </TableCell>
                <TableCell>
                  <DownloadLink
                    runId={run.id}
                    hasDownload={run.has_download}
                    label=""
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {data.count} run{data.count === 1 ? "" : "s"} total · page {page + 1}{" "}
          of {totalPages}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => navigate({ search: { page: page - 1 } })}
          >
            <ChevronLeft /> Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page + 1 >= totalPages}
            onClick={() => navigate({ search: { page: page + 1 } })}
          >
            Next <ChevronRight />
          </Button>
        </div>
      </div>
    </div>
  )
}

function RouteComponent() {
  const { page } = Route.useSearch()
  return (
    <div className="mx-auto max-w-5xl p-6 md:p-8">
      <CollectionsNav />
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Runs</h1>
        <p className="text-muted-foreground">
          Every workbook uploaded so far, newest first.
        </p>
      </div>
      <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg" />}>
        <RunsTable page={page} />
      </Suspense>
    </div>
  )
}
