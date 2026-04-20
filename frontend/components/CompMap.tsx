"use client";

import dynamic from "next/dynamic";
import { CompResponse } from "@/lib/types";

// React-Leaflet pulls `window` — lazy-load so SSR doesn't explode.
const InnerMap = dynamic(() => import("./CompMapInner"), {
  ssr: false,
  loading: () => (
    <div className="h-[360px] rounded-lg bg-slate-100 flex items-center justify-center text-slate-500">
      Loading map…
    </div>
  ),
});

export function CompMap({
  subjectLat, subjectLng, comps,
}: {
  subjectLat?: number | null;
  subjectLng?: number | null;
  comps: CompResponse[];
}) {
  if (!subjectLat || !subjectLng) {
    return (
      <div className="h-[360px] rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 text-sm">
        No coordinates yet — waiting on geocoding.
      </div>
    );
  }
  return <InnerMap subjectLat={subjectLat} subjectLng={subjectLng} comps={comps} />;
}
