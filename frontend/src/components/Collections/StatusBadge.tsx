import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const STYLES: Record<string, string> = {
  PASSED: "border-transparent bg-green-600 text-white",
  BLOCKED: "border-transparent bg-amber-500 text-white",
  FAILED: "border-transparent bg-destructive text-white",
  RUNNING: "border-transparent bg-blue-500 text-white",
  PENDING: "",
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={cn(STYLES[status])}>
      {status}
    </Badge>
  )
}
