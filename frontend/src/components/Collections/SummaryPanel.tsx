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

function Stat({
  label,
  value,
  title,
}: {
  label: string
  value: string | number
  title?: string
}) {
  return (
    <div title={title ?? String(value)}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}

const SOURCE_LABEL: Record<string, string> = {
  ollama: "Local LLM (Ollama, phi4-mini)",
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

      <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/[0.03]">
        <CardHeader className="flex-row items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          <CardTitle className="text-base font-semibold">AI Analysis</CardTitle>
          {summary.summary_source && (
            <Badge
              variant="secondary"
              className="ml-auto"
              title="Which rung of the three-rung fallback chain wrote this: local Ollama, an optional cloud model, or the deterministic Jinja template if neither was reachable"
            >
              {SOURCE_LABEL[summary.summary_source] ?? summary.summary_source}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-line text-base leading-relaxed text-foreground/90">
            {summary.narrative}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6 rounded-lg border p-6 md:grid-cols-4">
        <Stat label="Customers" value={summary.customer_count ?? "—"} />
        <Stat label="Invoices" value={summary.invoice_count ?? "—"} />
        <Stat label="Overdue" value={summary.overdue_count ?? "—"} />
        <Stat
          label="Outstanding"
          value={formatMoney(summary.total_outstanding)}
          title={summary.total_outstanding ?? undefined}
        />
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold">By region</h2>
        <div className="overflow-x-auto rounded-lg border">
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
                  <TableCell className="text-right" title={region.outstanding}>
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
