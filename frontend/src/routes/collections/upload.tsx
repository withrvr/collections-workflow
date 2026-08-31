import { useMutation } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { AlertTriangle, UploadCloud } from "lucide-react"
import { useRef, useState } from "react"

import { CollectionsService } from "@/client"
import { CollectionsNav } from "@/components/Collections/Nav"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { LoadingButton } from "@/components/ui/loading-button"

export const Route = createFileRoute("/collections/upload")({
  component: RouteComponent,
  head: () => ({
    meta: [{ title: "Upload workbook - Collections" }],
  }),
})

function RouteComponent() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const uploadMutation = useMutation({
    mutationFn: async (file: File) =>
      (await CollectionsService.createRun({ body: { file } })).data,
    onSuccess: (run) => {
      if (!run) return
      navigate({
        to: "/collections/run-detail",
        search: { runId: run.id },
      })
    },
  })

  return (
    <div className="mx-auto max-w-2xl p-6 md:p-8">
      <CollectionsNav />
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Upload a workbook</h1>
        <p className="text-muted-foreground">
          Upload an ERP export (Customers, Invoices, Payments, Region_Mapping
          sheets) to compute the overdue collections position and see every
          data-quality issue found along the way.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workbook file</CardTitle>
          <CardDescription>
            .xlsx file. Processing runs immediately — you'll be taken to the
            run's detail page as soon as it finishes.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-10 text-center text-muted-foreground hover:border-primary hover:text-foreground"
          >
            <UploadCloud className="size-8" />
            {selectedFile ? (
              <span className="font-medium text-foreground">
                {selectedFile.name}
              </span>
            ) : (
              <span>Click to choose a file, or drop one here</span>
            )}
          </button>

          {uploadMutation.isError && (
            <Alert variant="destructive">
              <AlertTriangle />
              <AlertTitle>Upload failed</AlertTitle>
              <AlertDescription>
                The request itself failed — this is different from a run that
                completes but is marked FAILED (that still shows its results).
                Check the backend is reachable and try again.
              </AlertDescription>
            </Alert>
          )}

          <LoadingButton
            disabled={!selectedFile}
            loading={uploadMutation.isPending}
            onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}
          >
            Run
          </LoadingButton>
        </CardContent>
      </Card>
    </div>
  )
}
