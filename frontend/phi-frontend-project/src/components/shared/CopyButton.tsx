import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { copyToClipboard } from "@/lib/utils";
import { toast } from "sonner";

interface CopyButtonProps extends Omit<ButtonProps, "onClick"> {
  text: string;
  label?: string;
}

export function CopyButton({ text, label = "Copy", variant = "outline", size = "sm", ...props }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleClick = async () => {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 1800);
    } else {
      toast.error("Couldn't copy — try selecting the text manually");
    }
  };

  return (
    <Button variant={variant} size={size} onClick={handleClick} disabled={!text} {...props}>
      {copied ? <Check /> : <Copy />}
      {copied ? "Copied" : label}
    </Button>
  );
}
