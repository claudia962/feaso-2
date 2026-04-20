"use client";

import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { CompResponse } from "@/lib/types";

// Fix Leaflet default icon path issue with webpack bundles.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function CompMapInner({
  subjectLat, subjectLng, comps,
}: {
  subjectLat: number;
  subjectLng: number;
  comps: CompResponse[];
}) {
  useEffect(() => { /* keep hook symmetry for SSR */ }, []);

  return (
    <div className="h-[360px] rounded-lg overflow-hidden border border-slate-200">
      <MapContainer center={[subjectLat, subjectLng]} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
        />
        <Marker position={[subjectLat, subjectLng]}>
          <Popup>
            <strong>Subject property</strong>
          </Popup>
        </Marker>
        {comps
          .filter((c) => c.latitude != null && c.longitude != null)
          .map((c, i) => (
            <CircleMarker
              key={c.comp_listing_id || i}
              center={[c.latitude as number, c.longitude as number]}
              radius={6 + (c.similarity_score || 0) * 5}
              pathOptions={{
                color: "#AF7225",
                fillColor: "#AF7225",
                fillOpacity: 0.6 + (c.similarity_score || 0) * 0.3,
              }}
            >
              <Popup>
                <div className="text-xs">
                  <div className="font-semibold">{c.comp_name || c.comp_listing_id}</div>
                  <div>{c.bedrooms}BR · ${(c.avg_adr || 0).toFixed(0)}/night</div>
                  <div>${(c.annual_revenue || 0).toLocaleString()}/yr</div>
                  <div>
                    Similarity: {((c.similarity_score || 0) * 100).toFixed(0)}% · {(c.distance_km || 0).toFixed(1)}km
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}
