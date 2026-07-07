import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { RotateCcw, FileText } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { CopyButton } from "@/components/shared/CopyButton";
import { EmptyState } from "@/components/shared/EmptyState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestore } from "@/lib/hooks/useRestore";
import { useSettings } from "@/lib/hooks/useSettings";

interface RestoreFormValues {
  sessionId: string;
  redactedText: string;
}

export default function RestorePage() {
  const { settings } = useSettings();
  const restoreMutation = useRestore();
  const location = useLocation();
  const prefill = (location.state as Partial<RestoreFormValues> | null) ?? null;
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RestoreFormValues>({
    defaultValues: { sessionId: prefill?.sessionId ?? "", redactedText: prefill?.redactedText ?? "" },
  });

  useEffect(() => {
    if (prefill?.sessionId || prefill?.redactedText) {
      reset({ sessionId: prefill.sessionId ?? "", redactedText: prefill.redactedText ?? "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  const onSubmit = (values: RestoreFormValues) => {
    restoreMutation.mutate(
      { sessionId: values.sessionId.trim(), text: values.redactedText },
      {
        onSuccess: () => toast.success("Text restored"),
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <div>
      <PageHeader
        eyebrow="Workspace"
        title="Restore original text"
        description="Provide the session ID from a redaction and the pseudonymized text to recover the original values."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Session &amp; redacted text</CardTitle>
            <CardDescription>The session must still be active — mappings expire after 30 minutes.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
              <div className="space-y-1.5">
                <Label htmlFor="sessionId">Session ID</Label>
                <Input
                  id="sessionId"
                  placeholder="e.g. 8b2e7a20-4ce8-42c3-83d0-4d49b9a9c0f1"
                  className="font-data"
                  {...register("sessionId", { required: "Session ID is required" })}
                />
                {errors.sessionId && (
                  <p className="text-xs text-destructive">{errors.sessionId.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="redactedText">Redacted text</Label>
                <Textarea
                  id="redactedText"
                  placeholder="Patient [NAME_001] visited [FACILITY_001]…"
                  className="min-h-[220px] resize-y font-data text-[13px] leading-relaxed sm:text-sm"
                  {...register("redactedText", { required: "Redacted text is required" })}
                />
                {errors.redactedText && (
                  <p className="text-xs text-destructive">{errors.redactedText.message}</p>
                )}
              </div>

              <Button type="submit" loading={restoreMutation.isPending} className="w-full sm:w-auto">
                <RotateCcw /> Restore text
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Original text</CardTitle>
            <CardDescription>Restored via your backend's /restore endpoint.</CardDescription>
          </CardHeader>
          <CardContent>
            {restoreMutation.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : restoreMutation.data ? (
              <motion.div
                initial={settings.animationsEnabled ? { opacity: 0, y: 8 } : false}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="space-y-4"
              >
                <div className="rounded-lg border border-border/70 bg-muted/30 p-4 font-data text-[13px] leading-relaxed sm:text-sm">
                  {restoreMutation.data.text}
                </div>
                <CopyButton text={restoreMutation.data.text} label="Copy original text" />
              </motion.div>
            ) : (
              <EmptyState
                icon={FileText}
                title="Nothing restored yet"
                description="Submit a session ID and redacted text to see the original values here."
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
