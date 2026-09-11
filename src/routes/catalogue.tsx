import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DataBadge } from "@/components/DataBadge";

export const Route = createFileRoute("/catalogue")({
  head: () => ({
    meta: [
      { title: "Signal Catalogue — WaterTrace" },
      {
        name: "description",
        content:
          "Every WaterTrace water signal (W1–W5, A1–A2, X1–X6) with its use case, customer, market driver and partner.",
      },
      { property: "og:title", content: "Signal Catalogue — WaterTrace" },
      {
        property: "og:description",
        content: "Live and concept water signals, their customers and market drivers.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CataloguePage,
});

interface Row {
  id: string;
  name: string;
  status: "Live" | "Concept";
  useCase: string;
  customer: string;
  driver: string;
  partner: string;
}

const ROWS: Row[] = [
  { id: "W1", name: "Water Consumption Intensity", status: "Live", useCase: "Hourly indirect water accounting; grid input to facility footprint", customer: "DC operators, cloud/AI, corporates, ESG software", driver: "EED reporting & draft EU DC rating scheme; GRI 303; CDP; ESRS materiality", partner: "Electricity Maps" },
  { id: "W2", name: "Water Withdrawal Intensity", status: "Live", useCase: "Drought/permit/thermal-discharge exposure; withdrawal disclosure", customer: "Utilities, industrial buyers, ESG analysts", driver: "GRI 303-3; ESRS withdrawals; NJ water-source reporting", partner: "Electricity Maps" },
  { id: "W3", name: "Imported Water Share", status: "Live", useCase: "Cross-border water leakage; location/PPA strategy", customer: "EU corporates, NGOs, policy", driver: "Shift to hourly consumption-based accounting", partner: "Electricity Maps" },
  { id: "W4", name: "Water Forecast & Low-Water Windows", status: "Live", useCase: "Water-aware scheduling of flexible loads", customer: "AI/cloud schedulers, flex aggregators", driver: "AI load growth, local water opposition", partner: "Electricity Maps" },
  { id: "W5", name: "Water–Carbon–Price Optimiser", status: "Live", useCase: "Co-optimise cost, carbon, water; flag trade-offs", customer: "Energy managers, traders, DC operators", driver: "Negative prices (ES 596 h H1 2026), heatwave spikes", partner: "Electricity Maps" },
  { id: "A1", name: "Facility Water Footprint", status: "Live", useCase: "EED/rating prep, RFPs, per-job AI water", customer: "DC operators, AI labs", driver: "EED, EU rating scheme, Water Resilience Strategy, NJ law", partner: "Electricity Maps (+X6)" },
  { id: "A2", name: "Zone Benchmark & Siting", status: "Live", useCase: "Siting, cloud-region choice", customer: "Developers, hyperscalers, investors", driver: "AI siting under grid/water limits", partner: "Electricity Maps" },
  { id: "X1", name: "Water-Stress-Weighted Intensity", status: "Concept", useCase: "Consumption in areas at water risk; siting", customer: "CSRD reporters, developers", driver: "ESRS E3-4 water-risk areas; CDP", partner: "WRI/WULCA, GEM" },
  { id: "X2", name: "Satellite Cooling Intelligence", status: "Concept", useCase: "Plant-level cooling evidence; audit-grade factors", customer: "All users, auditors", driver: "Data assurance", partner: "Satellite partner (e.g. AiDASH), Copernicus" },
  { id: "X3", name: "Heat-Adjusted Evaporation", status: "Concept", useCase: "Summer peaks, heatwave forecasts", customer: "DC operators, utilities", driver: "Heatwaves", partner: "Copernicus/ECMWF" },
  { id: "X4", name: "Reservoir Evaporation", status: "Concept", useCase: "Fair hydro accounting", customer: "Hydro-heavy grids", driver: "Hydro is the largest uncertainty", partner: "Copernicus, satellite partner" },
  { id: "X5", name: "Cooling-Water Derating & Price-Spike Risk", status: "Concept", useCase: "Trading/hedging alerts", customer: "Traders, utilities, TSOs", driver: "Summer derating, volatility", partner: "Copernicus, hydrology agencies" },
  { id: "X6", name: "Site Telemetry Fusion", status: "Concept", useCase: "Measured facility footprints", customer: "DC operators", driver: "EED accuracy, ratings", partner: "DCIM/BMS vendors" },
];

interface ApiRow {
  endpoint: string;
  fields: string;
  purpose: string;
  signals: string;
}

const API_ROWS: ApiRow[] = [
  {
    endpoint: "/v4/electricity-mix/latest",
    fields: "powerConsumptionBreakdown / powerProductionBreakdown (MW by source), powerImportBreakdown, zone, datetime",
    purpose: "Hourly generation and consumption mix; multiplied by the water factors to give the current L/kWh",
    signals: "W1, W2, W3",
  },
  {
    endpoint: "/v4/electricity-mix/history",
    fields: "Same breakdown, last 24 hours",
    purpose: "24-hour water-intensity trend and origin-vs-consumption comparison",
    signals: "W1, W2, W3",
  },
  {
    endpoint: "/v4/electricity-mix/past-range",
    fields: "Hourly flow-traced breakdown over a date range",
    purpose: "30-day zone averages and min–max ranges",
    signals: "A2",
  },
  {
    endpoint: "/v4/electricity-flows/latest & /history",
    fields: "Imports and exports per neighbouring zone (MW)",
    purpose: "One-hop tracing of water embedded in imported electricity",
    signals: "W3, W1 (flow-traced)",
  },
  {
    endpoint: "/v4/carbon-intensity/forecast",
    fields: "carbonIntensity (gCO2eq/kWh) per hour, 72 h",
    purpose: "Carbon leg of the combined score and trade-off view",
    signals: "W5",
  },
  {
    endpoint: "/v4/carbon-intensity/past-range",
    fields: "Hourly carbon intensity over a date range",
    purpose: "Carbon axis of the zone benchmark scatter",
    signals: "A2",
  },
  {
    endpoint: "/v4/price-day-ahead/forecast",
    fields: "price (EUR/MWh) per hour",
    purpose: "Price leg of the combined score",
    signals: "W5",
  },
  {
    endpoint: "Forecast mix (electricity-mix forecast horizon)",
    fields: "Hourly forecast breakdown, up to 72 h",
    purpose: "72-hour water forecast, low/medium/high hours and best job window",
    signals: "W4, W5",
  },
];

function CataloguePage() {
  const [status, setStatus] = useState<"all" | "Live" | "Concept">("all");
  const [term, setTerm] = useState("");

  const rows = ROWS.filter((r) => (status === "all" ? true : r.status === status)).filter((r) =>
    term
      ? `${r.id} ${r.name} ${r.useCase} ${r.customer} ${r.driver} ${r.partner}`
          .toLowerCase()
          .includes(term.toLowerCase())
      : true,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Signal catalogue"
        description="Every WaterTrace signal, who it is for and what makes it commercially interesting."
      />

      <div className="flex flex-wrap items-center gap-3">
        <Tabs value={status} onValueChange={(v) => setStatus(v as "all" | "Live" | "Concept")}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="Live">Live</TabsTrigger>
            <TabsTrigger value="Concept">Concept</TabsTrigger>
          </TabsList>
        </Tabs>
        <Input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Filter signals…"
          className="max-w-xs"
        />
      </div>

      <Card>
        <CardContent className="overflow-x-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14">ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Use case</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Market driver</TableHead>
                <TableHead>Partner</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs font-semibold">{r.id}</TableCell>
                  <TableCell className="min-w-[200px] font-medium">{r.name}</TableCell>
                  <TableCell>
                    <DataBadge kind={r.status === "Live" ? "live" : "mock"} />
                  </TableCell>
                  <TableCell className="min-w-[240px] text-sm text-muted-foreground">{r.useCase}</TableCell>
                  <TableCell className="min-w-[200px] text-sm text-muted-foreground">{r.customer}</TableCell>
                  <TableCell className="min-w-[240px] text-sm text-muted-foreground">{r.driver}</TableCell>
                  <TableCell className="min-w-[180px] text-sm text-muted-foreground">{r.partner}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold">Electricity Maps data used</h2>
          <DataBadge kind="live" />
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Every live signal is computed at request time from these Electricity Maps endpoints, combined with
          public water factors (Macknick et al. 2012) and the illustrative cooling profiles.
        </p>
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Endpoint</TableHead>
                  <TableHead>Fields used</TableHead>
                  <TableHead>What it powers</TableHead>
                  <TableHead>Signals</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {API_ROWS.map((r) => (
                  <TableRow key={r.endpoint}>
                    <TableCell className="min-w-[240px] font-mono text-xs">{r.endpoint}</TableCell>
                    <TableCell className="min-w-[260px] text-sm text-muted-foreground">{r.fields}</TableCell>
                    <TableCell className="min-w-[260px] text-sm text-muted-foreground">{r.purpose}</TableCell>
                    <TableCell className="min-w-[120px] text-sm font-medium">{r.signals}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
