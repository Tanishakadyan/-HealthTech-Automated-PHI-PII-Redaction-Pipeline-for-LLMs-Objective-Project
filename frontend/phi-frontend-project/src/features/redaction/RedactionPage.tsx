import { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Eraser, Download, KeyRound, RotateCcw, ShieldOff } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { CopyButton } from "@/components/shared/CopyButton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { DetectedEntities } from "@/features/redaction/components/DetectedEntities";
import { useRedact } from "@/lib/hooks/useRedact";
import { useKeyboardShortcut } from "@/lib/hooks/useKeyboardShortcut";
import { useSettings } from "@/lib/hooks/useSettings";
import { MAX_REDACTION_CHARS } from "@/lib/constants/limits";
import { cn } from "@/lib/utils";

const SAMPLE_TEXT =
  "Patient John Smith (MRN: 1234567, DOB 04/12/1979) was seen at Apollo General Hospital. Contact number +1 415-555-0148, email john.smith@example.com. SSN 123-45-6789.";

export default function RedactionPage() {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { settings } = useSettings();
  const redactMutation = useRedact();

  const charCount = text.length;
  const wordCount = useMemo(
    () => (text.trim().length === 0 ? 0 : text.trim().split(/\s+/).length),
    [text],
  );
  const overLimit = charCount > MAX_REDACTION_CHARS;

  const handleRedact = () => {
    const trimmed = text.trim();
    if (!trimmed) {
      toast.error("Paste some clinical text first");
      textareaRef.current?.focus();
      return;
    }
    if (overLimit) {
      toast.error(`Text exceeds the ${MAX_REDACTION_CHARS.toLocaleString()} character limit`);
      return;
    }
    redactMutation.mutate(text, {
      onSuccess: () => toast.success("Redaction complete"),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleReset = () => {
    setText("");
    redactMutation.reset();
    textareaRef.current?.focus();
  };

  useKeyboardShortcut({
    key: "Enter",
    ctrlOrCmd: true,
    onTrigger: handleRedact,
  });

  useKeyboardShortcut({
    key: "r",
    ctrlOrCmd: true,
    shift: true,
    onTrigger: handleReset,
  });

  const response = redactMutation.data ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Workspace"
        title="Redact clinical text"
        description="Paste PHI/PII-bearing text below. Detected entities are swapped for numbered, reversible tokens."
        actions={
          <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE_TEXT)}>
            Load sample
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Source text</CardTitle>
              <CardDescription>Never stored — sent directly to your backend.</CardDescription>
            </div>
            <ShieldOff className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste medical text here… (⌃/⌘+Enter to redact)"
              className={cn(
                "min-h-[280px] resize-y font-data text-[13px] leading-relaxed sm:text-sm",
                overLimit && "border-destructive focus-visible:ring-destructive",
              )}
              maxLength={MAX_REDACTION_CHARS + 500}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <div className="flex gap-4">
                <span>
                  <span className={cn("font-data font-semibold", overLimit && "text-destructive")}>
                    {charCount.toLocaleString()}
                  </span>{" "}
                  / {MAX_REDACTION_CHARS.toLocaleString()} chars
                </span>
                <span>
                  <span className="font-data font-semibold text-foreground">{wordCount.toLocaleString()}</span> words
                </span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleReset} disabled={!text && !response}>
                  <RotateCcw /> Reset
                </Button>
                <Button size="sm" onClick={handleRedact} loading={redactMutation.isPending}>
                  <Eraser /> Redact
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Redacted result</CardTitle>
              <CardDescription>Pseudonymized text and session for later restore.</CardDescription>
            </div>
            {response && (
              <Badge variant="accent">
                <KeyRound /> {response.session_id.slice(0, 8)}…
              </Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {redactMutation.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-4/6" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : response ? (
              <motion.div
                initial={settings.animationsEnabled ? { opacity: 0, y: 8 } : false}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="space-y-4"
              >
                <div className="rounded-lg border border-border/70 bg-muted/30 p-4 font-data text-[13px] leading-relaxed sm:text-sm">
                  {response.redacted_text}
                </div>
                <div className="flex flex-wrap gap-2">
                  <CopyButton text={response.redacted_text} label="Copy redacted text" />
                  <CopyButton text={response.session_id} label="Copy session ID" variant="ghost" />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadText(response.redacted_text, response.session_id)}
                  >
                    <Download /> Download
                  </Button>
                </div>
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Detected entities
                  </p>
                  <DetectedEntities response={response} />
                </div>
              </motion.div>
            ) : (
              <DetectedEntities response={null} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function downloadText(text: string, sessionId: string) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `redacted-${sessionId.slice(0, 8)}.txt`;
  anchor.click();
  URL.revokeObjectURL(url);
}
