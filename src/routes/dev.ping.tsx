import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { Button } from "@/components/ui/button";
import { waterSignals } from "@/lib/waterSignals.functions";

export const Route = createFileRoute("/dev/ping")({
  head: () => ({
    meta: [
      { title: "WaterTrace dev ping" },
      { name: "description", content: "Internal endpoint check for the WaterTrace water signals service." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "WaterTrace dev ping" },
      { property: "og:description", content: "Internal endpoint check for the WaterTrace water signals service." },
    ],
  }),
  component: DevPing,
});

function DevPing() {
  const call = useServerFn(waterSignals);
  const [out, setOut] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function ping() {
    setLoading(true);
    try {
      const res = await call({ data: { action: "latest", zone: "DK-DK1" } });
      setOut(JSON.stringify(res, null, 2));
    } catch (e) {
      setOut(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-6 space-y-4">
      <h1 className="text-xl font-semibold">Dev ping — water-signals</h1>
      <Button onClick={ping} disabled={loading}>
        {loading ? "Calling…" : "Call latest / DK-DK1"}
      </Button>
      <pre className="overflow-auto rounded-md border bg-muted p-4 text-xs">{out || "No response yet."}</pre>
    </main>
  );
}
