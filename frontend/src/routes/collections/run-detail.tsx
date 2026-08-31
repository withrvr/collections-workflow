import { createFileRoute } from "@tanstack/react-router"

// Run detail with the stage timeline. Built in Phase 8 (MASTER_PLAN.md).
export const Route = createFileRoute("/collections/run-detail")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Collections run detail — built in Phase 8.</div>
}
