import { useMutation } from "@tanstack/react-query";
import { restoreText } from "@/lib/api/redaction";

export function useRestore() {
  return useMutation({
    mutationFn: ({ sessionId, text }: { sessionId: string; text: string }) =>
      restoreText(sessionId, text),
  });
}
