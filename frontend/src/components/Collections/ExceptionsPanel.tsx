import { useSuspenseQuery } from "@tanstack/react-query"
import { ChevronDown, ShieldCheck } from "lucide-react"
import { useState } from "react"

import { CollectionsService, type ExceptionOut } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const SOURCE_LABEL: Record<string, string> = {
  ollama: "Local LLM (Ollama)",
  cloud: "Cloud LLM",
  fallback: "Deterministic",
}

/** One exception, as a card -- not a table row. A `<table>` forces every
 * cell in a column to share one width, which is exactly what broke here:
 * long cause/impact/fix text either got clipped or spilled across
 * neighboring columns once expanded. A card has no such constraint --
 * text just wraps, full width, every time. */
function ExceptionCard({ row }: { row: ExceptionOut }) {
  const [open, setOpen] = useState(false)
  const recordId = row.invoice_id ?? row.payment_id ?? row.customer_id
  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 p-4 text-left hover:bg-muted/50"
      >
        <Badge
          variant={row.severity === "error" ? "destructive" : "secondary"}
          className="mt-0.5 shrink-0"
          title={
            row.severity === "error" ? "Error severity" : "Warning severity"
          }
        >
          {row.rule_code}
        </Badge>
        <div className="min-w-0 flex-1">
          <p className="font-medium" title={row.category}>
            {row.category}
            {recordId && (
              <span
                className="ml-2 font-mono text-xs font-normal text-muted-foreground"
                title={`Record: ${recordId}`}
              >
                {recordId}
              </span>
            )}
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">{row.message}</p>
        </div>
        <ChevronDown
          className={cn(
            "mt-1 size-4 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <div className="grid grid-cols-1 gap-4 border-t bg-muted/30 p-4 text-sm sm:grid-cols-2">
          <div>
            <p className="font-medium text-muted-foreground">Cause</p>
            <p className="mt-0.5">{row.cause}</p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Impact</p>
            <p className="mt-0.5">{row.impact}</p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Suggested fix</p>
            <p className="mt-0.5 font-medium text-foreground">
              {row.suggested_fix}
            </p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Owner</p>
            <p className="mt-0.5">{row.owner}</p>
          </div>
          {row.explanation_source && (
            <div className="sm:col-span-2">
              <Badge
                variant="outline"
                title="Which rung of the three-rung AI fallback chain wrote this explanation"
              >
                Explained by:{" "}
                {SOURCE_LABEL[row.explanation_source] ?? row.explanation_source}
              </Badge>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Fetches and renders one run's exceptions -- shared by the standalone
 * /collections/exceptions page and the all-in-one run-detail page, so
 * both stay in sync automatically. */
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
    <div className="flex flex-col gap-2">
      {rows.map((row) => (
        <ExceptionCard key={row.id} row={row} />
      ))}
      {limit && data.data.length > limit && (
        <p className="px-1 py-2 text-sm text-muted-foreground">
          Showing {limit} of {data.data.length} — click a card to expand, or
          open the full exceptions page to see the rest.
        </p>
      )}
    </div>
  )
}
