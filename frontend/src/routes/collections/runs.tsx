import { createFileRoute } from "@tanstack/react-router"

// Runs list. Built in Phase 8 (MASTER_PLAN.md).
export const Route = createFileRoute("/collections/runs")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Collections runs list — built in Phase 8.</div>
}
