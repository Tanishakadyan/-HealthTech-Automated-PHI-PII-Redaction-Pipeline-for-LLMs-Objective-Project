import { useState } from "react";
import { toast } from "sonner";
import { Download, Loader2, Save, Trash2, Wifi } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useSettings, type AccentTheme, type ColorMode } from "@/lib/hooks/useSettings";
import { useHistory } from "@/lib/hooks/useHistory";
import { fetchHealth } from "@/lib/api/redaction";

export default function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const { entries, exportHistory, clearHistory } = useHistory();
  const [backendUrlDraft, setBackendUrlDraft] = useState(settings.backendUrl);
  const [testing, setTesting] = useState(false);

  const handleSaveBackendUrl = () => {
    updateSettings({ backendUrl: backendUrlDraft.trim().replace(/\/+$/, "") });
    toast.success("Backend URL saved");
  };

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      updateSettings({ backendUrl: backendUrlDraft.trim().replace(/\/+$/, "") });
      const health = await fetchHealth();
      toast.success(`Connected — backend reports "${health.status}"`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Connection failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Preferences" title="Settings" description="Configure appearance, backend connection, and local data." />

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Color mode, accent theme, and motion preferences.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Label>Dark mode</Label>
              <p className="text-xs text-muted-foreground">Follow system, or force light/dark.</p>
            </div>
            <Select
              value={settings.colorMode}
              onValueChange={(v) => updateSettings({ colorMode: v as ColorMode })}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Label>Theme</Label>
              <p className="text-xs text-muted-foreground">Accent color used across the app.</p>
            </div>
            <Select
              value={settings.accentTheme}
              onValueChange={(v) => updateSettings({ accentTheme: v as AccentTheme })}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cyan">Cyan (default)</SelectItem>
                <SelectItem value="violet">Violet</SelectItem>
                <SelectItem value="emerald">Emerald</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="animations">Animations</Label>
              <p className="text-xs text-muted-foreground">
                Disable to reduce motion across pages and charts.
              </p>
            </div>
            <Switch
              id="animations"
              checked={settings.animationsEnabled}
              onCheckedChange={(checked) => updateSettings({ animationsEnabled: checked })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Backend connection</CardTitle>
          <CardDescription>Where the app sends /redact, /restore, and /health requests.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="backendUrl">Backend URL</Label>
          <Input
            id="backendUrl"
            value={backendUrlDraft}
            onChange={(e) => setBackendUrlDraft(e.target.value)}
            placeholder="http://localhost:8000"
            className="font-data"
          />
        </CardContent>
        <CardFooter className="gap-2">
          <Button onClick={handleSaveBackendUrl}>
            <Save /> Save
          </Button>
          <Button variant="outline" onClick={handleTestConnection} disabled={testing}>
            {testing ? <Loader2 className="animate-spin" /> : <Wifi />}
            Test connection
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Local data</CardTitle>
          <CardDescription>
            History ({entries.length} entries) and settings are stored only in this browser's
            localStorage — never on a server.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={exportHistory} disabled={entries.length === 0}>
            <Download /> Export history
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" disabled={entries.length === 0}>
                <Trash2 /> Clear cache
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Clear local cache?</AlertDialogTitle>
                <AlertDialogDescription>
                  This deletes all {entries.length} history entries stored in this browser.
                  Appearance and backend settings are kept. This can't be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => {
                    clearHistory();
                    toast.success("Cache cleared");
                  }}
                >
                  Clear cache
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
