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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"

const DEFAULT_REPORT_DATE = "2026-07-31"

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
  const [reportDate, setReportDate] = useState(DEFAULT_REPORT_DATE)
  const [dragOver, setDragOver] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: async ({
      file,
      report_date,
    }: {
      file: File
      report_date: string
    }) =>
      (await CollectionsService.createRun({ body: { file, report_date } }))
        .data,
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
          data-quality issue found along the way. File-level problems (a missing
          sheet, a corrupt file, an unreadable cell) are caught the same way
          row-level ones are — you'll see exactly what happened, never a raw
          error.
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
          {/* Native HTML5 drag-and-drop -- no library needed. */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              const dropped = e.dataTransfer.files?.[0]
              if (dropped) setSelectedFile(dropped)
            }}
            className={cn(
              "flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-10 text-center text-muted-foreground transition-colors hover:border-primary hover:text-foreground",
              dragOver && "border-primary bg-primary/5 text-foreground",
            )}
          >
            <UploadCloud className="size-8" />
            {selectedFile ? (
              <span className="font-medium text-foreground">
                {selectedFile.name}
              </span>
            ) : (
              <span>Click to choose a file, or drag one in</span>
            )}
          </button>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="report-date">Report date</Label>
            <Input
              id="report-date"
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              title="The date overdue/ageing math is anchored to. Defaults to the workbook's own stated report date -- change it to test a different scenario against the same file."
              className="w-48"
            />
          </div>

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
            onClick={() =>
              selectedFile &&
              uploadMutation.mutate({
                file: selectedFile,
                report_date: reportDate,
              })
            }
          >
            Run
          </LoadingButton>
        </CardContent>
      </Card>
    </div>
  )
}
