import { useNavigate, useSearch } from "@tanstack/react-router";
import { DEFAULT_ZONE, ZONE_KEYS } from "@/lib/zones";

export function useZone() {
  const search = useSearch({ strict: false }) as { zone?: string };
  const navigate = useNavigate();

  const zone = search.zone && ZONE_KEYS.includes(search.zone) ? search.zone : DEFAULT_ZONE;

  const setZone = (next: string) => {
    navigate({ to: ".", search: (prev) => ({ ...prev, zone: next }), replace: true });
  };

  return { zone, setZone };
}
