import { createFileRoute } from "@tanstack/react-router"

// Exceptions table with filters. Built in Phase 8 (MASTER_PLAN.md).
export const Route = createFileRoute("/collections/exceptions")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Collections exceptions table — built in Phase 8.</div>
}
