import { createFileRoute } from "@tanstack/react-router"

// Workbook upload. Built in Phase 8 (MASTER_PLAN.md).
export const Route = createFileRoute("/collections/upload")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Collections upload — built in Phase 8.</div>
}
