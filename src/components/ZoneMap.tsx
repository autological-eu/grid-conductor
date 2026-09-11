import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export interface ZoneMapPoint {
  zone: string;
  name: string;
  lat: number;
  lon: number;
  avg: number;
}

export default function ZoneMap({ points }: { points: ZoneMapPoint[] }) {
  const max = Math.max(1, ...points.map((p) => p.avg));
  return (
    <MapContainer
      center={[40, -20]}
      zoom={2}
      scrollWheelZoom={false}
      style={{ height: 420, width: "100%", borderRadius: 12 }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((p) => (
        <CircleMarker
          key={p.zone}
          center={[p.lat, p.lon]}
          radius={6 + (p.avg / max) * 22}
          pathOptions={{ color: "#1E88E5", fillColor: "#1E88E5", fillOpacity: 0.35 }}
        >
          <Popup>
            <strong>{p.name}</strong>
            <br />
            {p.zone}: {p.avg.toFixed(2)} L/kWh (30-day avg)
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
