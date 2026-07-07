import { useMutation } from "@tanstack/react-query";
import { redactText } from "@/lib/api/redaction";
import { useHistory } from "@/lib/hooks/useHistory";

export function useRedact() {
  const { addEntry } = useHistory();

  return useMutation({
    mutationFn: (text: string) => redactText(text),
    onSuccess: (response, originalText) => {
      addEntry(response, originalText.length);
    },
  });
}
