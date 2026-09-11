import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/stores/settings";

export function SettingsPopover() {
  const { includeHydro, mode, setIncludeHydro, setMode } = useSettings();
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Settings">
          <Settings2 className="size-5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <Label htmlFor="hydro" className="text-sm">
              Include hydro evaporation
            </Label>
            <p className="mt-1 text-xs text-muted-foreground">
              Reservoir evaporation is contested; off by default.
            </p>
          </div>
          <Switch id="hydro" checked={includeHydro} onCheckedChange={setIncludeHydro} />
        </div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <Label htmlFor="mode" className="text-sm">
              Origin tracing
            </Label>
            <p className="mt-1 text-xs text-muted-foreground">
              {mode === "origin"
                ? "One-hop flow tracing (slower, more calls)."
                : "Fast mode: domestic mix only."}
            </p>
          </div>
          <Switch
            id="mode"
            checked={mode === "origin"}
            onCheckedChange={(v) => setMode(v ? "origin" : "fast")}
          />
        </div>
      </PopoverContent>
    </Popover>
  );
}
