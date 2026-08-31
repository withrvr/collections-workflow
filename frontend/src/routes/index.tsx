import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowRight,
  FileSpreadsheet,
  ListChecks,
  UploadCloud,
} from "lucide-react"
import { Suspense } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

import { CollectionsService } from "@/client"
import { StatusBadge } from "@/components/Collections/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/")({
  component: Dashboard,
  head: () => ({
    meta: [{ title: "Dashboard - Collections Workflow" }],
  }),
})

const STATUS_COLOR: Record<string, string> = {
  PASSED: "#16a34a",
  BLOCKED: "#f59e0b",
  FAILED: "#dc2626",
  RUNNING: "#3b82f6",
  PENDING: "#94a3b8",
}

function formatMoney(value: string | null) {
  if (value === null) return "—"
  return `Rs ${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
}

function DashboardContent() {
  const { data } = useSuspenseQuery({
    queryFn: async () =>
      (await CollectionsService.listRuns({ query: { skip: 0, limit: 100 } }))
        .data,
    queryKey: ["collections", "runs", "dashboard"],
  })

  const runs = data.data
  const statusCounts = runs.reduce<Record<string, number>>((acc, r) => {
    acc[r.status] = (acc[r.status] ?? 0) + 1
    return acc
  }, {})
  const statusChartData = Object.entries(statusCounts).map(
    ([status, count]) => ({
      status,
      count,
      fill: STATUS_COLOR[status] ?? "#94a3b8",
    }),
  )

  const totalOutstanding = runs.reduce(
    (sum, r) => sum + (r.total_outstanding ? Number(r.total_outstanding) : 0),
    0,
  )
  const totalExceptions = runs.reduce(
    (sum, r) => sum + (r.exception_count ?? 0),
    0,
  )

  // Oldest-to-newest so the outstanding-over-time chart reads left-to-right.
  const outstandingSeries = [...runs]
    .reverse()
    .slice(-15)
    .map((r, i) => ({
      name: `#${i + 1}`,
      outstanding: r.total_outstanding ? Number(r.total_outstanding) : 0,
      status: r.status,
      title: r.source_filename,
    }))

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total runs</p>
            <p className="text-3xl font-bold">{data.count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Passed</p>
            <p className="text-3xl font-bold text-green-600">
              {statusCounts.PASSED ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Blocked</p>
            <p className="text-3xl font-bold text-amber-500">
              {statusCounts.BLOCKED ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Failed</p>
            <p className="text-3xl font-bold text-destructive">
              {statusCounts.FAILED ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Outstanding by run (last {outstandingSeries.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {outstandingSeries.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No runs yet — upload a workbook to see this fill in.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={outstandingSeries}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis
                    fontSize={12}
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  />
                  <RechartsTooltip
                    formatter={(value) => [
                      `Rs ${Number(value).toLocaleString("en-IN")}`,
                      "Outstanding",
                    ]}
                    labelFormatter={(_, payload) =>
                      (payload?.[0]?.payload as { title?: string } | undefined)
                        ?.title ?? ""
                    }
                  />
                  <Bar dataKey="outstanding" radius={[4, 4, 0, 0]}>
                    {outstandingSeries.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={STATUS_COLOR[entry.status] ?? "#0d9488"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Run outcomes</CardTitle>
          </CardHeader>
          <CardContent>
            {statusChartData.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No runs yet.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={statusChartData}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    // biome-ignore lint/suspicious/noExplicitAny: recharts' PieLabelRenderProps type doesn't include the custom data fields it passes at runtime
                    label={(props: any) => `${props.status} (${props.count})`}
                  >
                    {statusChartData.map((entry) => (
                      <Cell key={entry.status} fill={entry.fill} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card title={`Rs ${totalOutstanding.toLocaleString("en-IN")}`}>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Total outstanding across all runs
            </p>
            <p className="text-2xl font-bold">
              {formatMoney(String(totalOutstanding))}
            </p>
          </CardContent>
        </Card>
        <Card title={`${totalExceptions} exceptions`}>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Total exceptions found across all runs
            </p>
            <p className="text-2xl font-bold">{totalExceptions}</p>
          </CardContent>
        </Card>
      </div>

      {runs.length > 0 && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent runs</h2>
            <Link
              to="/collections/runs"
              search={{ page: 0 }}
              className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              View all <ArrowRight className="size-3.5" />
            </Link>
          </div>
          <div className="flex flex-col gap-2">
            {runs.slice(0, 5).map((run) => (
              <Link
                key={run.id}
                to="/collections/run-detail"
                search={{ runId: run.id }}
                className="flex items-center justify-between rounded-lg border p-3 hover:bg-muted/50"
              >
                <span className="font-medium" title={run.source_filename}>
                  {run.source_filename}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">
                    {formatMoney(run.total_outstanding)}
                  </span>
                  <StatusBadge status={run.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Dashboard() {
  return (
    <div className="mx-auto max-w-5xl p-6 md:p-8">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b pb-6">
        <div className="flex items-center gap-3">
          <img src="/logo.svg" alt="Collections Workflow" className="size-10" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Collections Workflow
            </h1>
            <p className="text-muted-foreground">
              Upload an ERP export, get an overdue collections position, a full
              data-quality report, and an AI-written summary — all automated,
              all local.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link to="/collections/upload">
            <Button>
              <UploadCloud /> Upload a workbook
            </Button>
          </Link>
          <Link to="/collections/runs" search={{ page: 0 }}>
            <Button variant="outline">
              <ListChecks /> All runs
            </Button>
          </Link>
        </div>
      </header>

      <Suspense
        fallback={
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton count
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        }
      >
        <DashboardContent />
      </Suspense>

      {/* Quick nav for anyone landing without a run yet. */}
      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link
          to="/collections/upload"
          className="flex items-center gap-3 rounded-lg border p-4 hover:bg-muted/50"
        >
          <FileSpreadsheet className="size-6 text-primary" />
          <div>
            <p className="font-medium">Start a new run</p>
            <p className="text-sm text-muted-foreground">
              Upload a workbook, get results in seconds
            </p>
          </div>
        </Link>
        <Link
          to="/collections/runs"
          search={{ page: 0 }}
          className="flex items-center gap-3 rounded-lg border p-4 hover:bg-muted/50"
        >
          <ListChecks className="size-6 text-primary" />
          <div>
            <p className="font-medium">Browse past runs</p>
            <p className="text-sm text-muted-foreground">
              Every run so far, with full history
            </p>
          </div>
        </Link>
      </div>
    </div>
  )
}
