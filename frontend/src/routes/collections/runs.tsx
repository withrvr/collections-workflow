import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FileQuestion } from "lucide-react"
import { Suspense } from "react"

import { CollectionsService } from "@/client"
import { CollectionsNav } from "@/components/Collections/Nav"
import { StatusBadge } from "@/components/Collections/StatusBadge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function getRunsQueryOptions() {
  return {
    queryFn: async () =>
      (await CollectionsService.listRuns({ query: { skip: 0, limit: 100 } }))
        .data,
    queryKey: ["collections", "runs"],
  }
}

export const Route = createFileRoute("/collections/runs")({
  component: RouteComponent,
  head: () => ({
    meta: [{ title: "Runs - Collections" }],
  }),
})

function formatMoney(value: string | null) {
  if (value === null) return "—"
  return `Rs ${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function RunsTable() {
  const { data } = useSuspenseQuery(getRunsQueryOptions())

  if (data.data.length === 0) {
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

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>File</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Overdue</TableHead>
            <TableHead className="text-right">Outstanding</TableHead>
            <TableHead className="text-right">Exceptions</TableHead>
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
                >
                  {run.source_filename}
                </Link>
              </TableCell>
              <TableCell>
                <StatusBadge status={run.status} />
              </TableCell>
              <TableCell className="text-muted-foreground">
                {new Date(run.created_at).toLocaleString()}
              </TableCell>
              <TableCell className="text-right">
                {run.overdue_count ?? "—"}
              </TableCell>
              <TableCell className="text-right">
                {formatMoney(run.total_outstanding)}
              </TableCell>
              <TableCell className="text-right">
                {run.exception_count ?? "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function RouteComponent() {
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
        <RunsTable />
      </Suspense>
    </div>
  )
}
