import { useMutation } from "@tanstack/react-query"
import { Mail } from "lucide-react"
import { useState } from "react"

import { CollectionsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"

/** Emails a finished run's summary -- status, key numbers, the AI
 * narrative -- to whoever needs it, via the same SMTP config the
 * template already uses elsewhere (Mailpit in dev). A human clicks this
 * for a specific run, on purpose, every time -- not an auto-send. */
export function SendEmailButton({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState("")
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async (to: string) =>
      (
        await CollectionsService.sendRunEmail({
          path: { run_id: runId },
          body: { to },
        })
      ).data,
    onSuccess: () => {
      showSuccessToast(`Sent to ${email}. Check Mailpit at :8025 in dev.`)
      setOpen(false)
      setEmail("")
    },
    onError: () =>
      showErrorToast("Could not send the email -- is SMTP configured?"),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" title="Email this run's summary">
          <Mail /> Email summary
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Email this run's summary</DialogTitle>
          <DialogDescription>
            Sends the status, key numbers, and the AI narrative as a formatted
            email.
          </DialogDescription>
        </DialogHeader>
        <Input
          type="email"
          placeholder="reviewer@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && email) mutation.mutate(email)
          }}
        />
        <DialogFooter>
          <LoadingButton
            disabled={!email}
            loading={mutation.isPending}
            onClick={() => mutation.mutate(email)}
          >
            Send
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
