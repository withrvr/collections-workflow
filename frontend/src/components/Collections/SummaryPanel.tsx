import { useSuspenseQuery } from "@tanstack/react-query"
import { CheckCircle2, ShieldAlert, Sparkles } from "lucide-react"

import { CollectionsService } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function formatMoney(value: string | null) {
  if (value === null) return "—"
  return `Rs ${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatRate(value: string | null) {
  if (value === null) return "—"
  return `${(Number(value) * 100).toFixed(1)}%`
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}

const SOURCE_LABEL: Record<string, string> = {
  ollama: "Local LLM (Ollama)",
  cloud: "Cloud LLM",
  fallback: "Deterministic template",
}

/** Fetches and renders one run's full summary -- block/pass banner,
 * AI narrative with its source, numeric stats, region breakdown.
 * Shared by the standalone /collections/summary page and the
 * all-in-one run-detail page. */
export function SummaryPanel({ runId }: { runId: string }) {
  const { data: summary } = useSuspenseQuery({
    queryFn: async () =>
      (await CollectionsService.getSummary({ query: { run_id: runId } })).data,
    queryKey: ["collections", "summary", runId],
  })

  if (!summary) return null
  const blocked = summary.status === "BLOCKED"

  return (
    <div className="flex flex-col gap-6">
      {summary.status === "PASSED" || summary.status === "BLOCKED" ? (
        <Alert variant={blocked ? "destructive" : "default"}>
          {blocked ? <ShieldAlert /> : <CheckCircle2 />}
          <AlertTitle>
            {blocked
              ? `Blocked — exception rate ${formatRate(summary.exception_row_rate)} exceeds the ${formatRate(summary.gate_threshold)} control threshold`
              : `Passed — exception rate ${formatRate(summary.exception_row_rate)} is within the ${formatRate(summary.gate_threshold)} control threshold`}
          </AlertTitle>
          <AlertDescription>
            {summary.exception_count} exception
            {summary.exception_count === 1 ? "" : "s"} found,{" "}
            {summary.distinct_invoices_affected} distinct invoice
            {summary.distinct_invoices_affected === 1 ? "" : "s"} affected (
            {formatRate(summary.distinct_invoice_rate)} of invoices).
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="flex-row items-center gap-2">
          <Sparkles className="size-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Narrative
          </CardTitle>
          {summary.summary_source && (
            <Badge variant="secondary" className="ml-auto">
              {SOURCE_LABEL[summary.summary_source] ?? summary.summary_source}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          <p className="leading-relaxed">{summary.narrative}</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6 rounded-lg border p-6 md:grid-cols-4">
        <Stat label="Customers" value={summary.customer_count ?? "—"} />
        <Stat label="Invoices" value={summary.invoice_count ?? "—"} />
        <Stat label="Overdue" value={summary.overdue_count ?? "—"} />
        <Stat
          label="Outstanding"
          value={formatMoney(summary.total_outstanding)}
        />
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold">By region</h2>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Region</TableHead>
                <TableHead className="text-right">Overdue invoices</TableHead>
                <TableHead className="text-right">Outstanding</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summary.by_region.map((region) => (
                <TableRow key={region.region}>
                  <TableCell className="font-medium">{region.region}</TableCell>
                  <TableCell className="text-right">
                    {region.overdue_count}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(region.outstanding)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
