import { useSuspenseQuery } from "@tanstack/react-query"
import { ChevronDown, ShieldCheck } from "lucide-react"
import { useState } from "react"

import { CollectionsService, type ExceptionOut } from "@/client"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

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
                <dd className="font-medium text-foreground">
                  {row.suggested_fix}
                </dd>
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

/** Fetches and renders one run's exceptions table -- shared by the
 * standalone /collections/exceptions page and the all-in-one run-detail
 * page, so both stay in sync automatically. */
export function ExceptionsPanel({
  runId,
  ruleCode,
  severity,
  limit,
}: {
  runId: string
  ruleCode?: string
  severity?: string
  /** Cap rows shown (e.g. a compact preview on run-detail). Omit to show all. */
  limit?: number
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

  const rows = limit ? data.data.slice(0, limit) : data.data

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
          {rows.map((row) => (
            <ExceptionRow key={row.id} row={row} />
          ))}
        </TableBody>
      </Table>
      {limit && data.data.length > limit && (
        <p className="border-t px-4 py-2 text-sm text-muted-foreground">
          Showing {limit} of {data.data.length} — click a row to expand, or open
          the full exceptions page to see the rest.
        </p>
      )}
    </div>
  )
}
