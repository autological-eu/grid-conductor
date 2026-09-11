import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PILOT_ZONES } from "@/lib/zones";
import { useZone } from "@/hooks/useZone";

export function ZoneSelector({ className }: { className?: string }) {
  const { zone, setZone } = useZone();
  const eu = PILOT_ZONES.filter((z) => z.group === "EU");
  const us = PILOT_ZONES.filter((z) => z.group === "US");

  return (
    <Select value={zone} onValueChange={setZone}>
      <SelectTrigger className={className} aria-label="Select zone">
        <SelectValue placeholder="Select zone" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>EU</SelectLabel>
          {eu.map((z) => (
            <SelectItem key={z.key} value={z.key}>
              <span className="font-mono text-xs text-muted-foreground">{z.key}</span>
              <span className="ml-2">{z.label}</span>
            </SelectItem>
          ))}
        </SelectGroup>
        <SelectGroup>
          <SelectLabel>US</SelectLabel>
          {us.map((z) => (
            <SelectItem key={z.key} value={z.key}>
              <span className="font-mono text-xs text-muted-foreground">{z.key}</span>
              <span className="ml-2">{z.label}</span>
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
