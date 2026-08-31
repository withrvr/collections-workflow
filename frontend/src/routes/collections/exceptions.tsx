import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ChevronDown, ShieldCheck } from "lucide-react"
import { Suspense, useState } from "react"
import { z } from "zod"

import { CollectionsService, type ExceptionOut } from "@/client"
import { CollectionsNav } from "@/components/Collections/Nav"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

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

function ExceptionRow({ row }: { row: ExceptionOut }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={() => setOpen((v) => !v)}
      >
        <TableCell>
          <Badge
            variant={row.severity === "error" ? "destructive" : "secondary"}
          >
            {row.rule_code}
          </Badge>
        </TableCell>
        <TableCell>{row.category}</TableCell>
        <TableCell className="max-w-md truncate">{row.message}</TableCell>
        <TableCell className="font-mono text-xs text-muted-foreground">
          {row.invoice_id ?? row.payment_id ?? row.customer_id ?? "—"}
        </TableCell>
        <TableCell>
          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
          />
        </TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={5} className="bg-muted/30">
            <dl className="grid grid-cols-1 gap-3 py-2 text-sm md:grid-cols-2">
              <div>
                <dt className="font-medium text-muted-foreground">Cause</dt>
                <dd>{row.cause}</dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Impact</dt>
                <dd>{row.impact}</dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">
                  Suggested fix
                </dt>
                <dd>{row.suggested_fix}</dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Owner</dt>
                <dd>{row.owner}</dd>
              </div>
            </dl>
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

function ExceptionsTable({
  runId,
  ruleCode,
  severity,
}: {
  runId: string
  ruleCode?: string
  severity?: string
}) {
  const { data } = useSuspenseQuery({
    queryFn: async () =>
      (
        await CollectionsService.getExceptions({
          query: { run_id: runId, rule_code: ruleCode, severity },
        })
      ).data,
    queryKey: ["collections", "exceptions", runId, ruleCode, severity],
  })

  if (!data || data.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-16 text-center">
        <ShieldCheck className="size-8 text-green-600" />
        <div>
          <p className="font-medium">No exceptions match this filter</p>
          <p className="text-sm text-muted-foreground">
            Clear the filters to see the full list, if any.
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
            <TableHead>Rule</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Message</TableHead>
            <TableHead>Record</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.data.map((row) => (
            <ExceptionRow key={row.id} row={row} />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

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
        <ExceptionsTable
          runId={runId}
          ruleCode={ruleCode}
          severity={severity}
        />
      </Suspense>
    </div>
  )
}
