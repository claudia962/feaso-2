"use client";

import { useMemo, useState } from "react";
import { aud, pct } from "@/lib/format";

interface RenovationOption {
  item: string;
  label: string;
  estimated_cost: number;
  adr_lift_per_night: number;
  occupancy_lift: number;
}

const DEFAULT_OPTIONS: RenovationOption[] = [
  { item: "hot_tub",          label: "Hot tub",               estimated_cost: 8000,  adr_lift_per_night: 52, occupancy_lift: 0.04 },
  { item: "pool",             label: "Pool",                  estimated_cost: 45000, adr_lift_per_night: 85, occupancy_lift: 0.05 },
  { item: "kitchen_upgrade",  label: "Kitchen upgrade",       estimated_cost: 18000, adr_lift_per_night: 28, occupancy_lift: 0.02 },
  { item: "bathroom_upgrade", label: "Bathroom upgrade",      estimated_cost: 12000, adr_lift_per_night: 18, occupancy_lift: 0.01 },
  { item: "extra_bedroom",    label: "Extra bedroom",         estimated_cost: 25000, adr_lift_per_night: 55, occupancy_lift: 0.03 },
  { item: "outdoor_area",     label: "Outdoor entertaining",  estimated_cost: 14000, adr_lift_per_night: 22, occupancy_lift: 0.02 },
  { item: "smart_home",       label: "Smart home package",    estimated_cost: 4500,  adr_lift_per_night: 12, occupancy_lift: 0.01 },
  { item: "ev_charger",       label: "EV charger",            estimated_cost: 3500,  adr_lift_per_night: 8,  occupancy_lift: 0.01 },
];

/**
 * Let the user toggle amenities and see cumulative cost + revenue lift +
 * blended payback. Based on market-generic deltas — real comp-pair evidence
 * comes from `/api/renovations/:id` when wired.
 */
export function RenovationCalculator({
  baseAdr = 220,
  baseOccupancy = 0.65,
}: {
  baseAdr?: number;
  baseOccupancy?: number;
}) {
  const [picked, setPicked] = useState<Record<string, boolean>>({});

  const totals = useMemo(() => {
    let cost = 0;
    let adrLift = 0;
    let occLift = 0;
    for (const opt of DEFAULT_OPTIONS) {
      if (picked[opt.item]) {
        cost += opt.estimated_cost;
        adrLift += opt.adr_lift_per_night;
        occLift += opt.occupancy_lift;
      }
    }
    const nights = 365 * Math.min(0.97, baseOccupancy + occLift);
    const revenueLift = nights * adrLift + 365 * baseAdr * occLift;
    const paybackNights = revenueLift > 0 ? cost / (revenueLift / 365) : 0;
    return {
      cost,
      adrLift,
      occLift,
      revenueLift,
      paybackNights,
      paybackMonths: paybackNights / 30,
      roi: cost > 0 ? revenueLift / cost : 0,
    };
  }, [picked, baseAdr, baseOccupancy]);

  return (
    <div className="grid md:grid-cols-[1fr,320px] gap-6">
      <div className="space-y-2">
        {DEFAULT_OPTIONS.map((opt) => {
          const on = !!picked[opt.item];
          return (
            <label
              key={opt.item}
              className={`flex items-center justify-between p-3 rounded-lg border transition
                ${on ? "bg-amber-50 border-[#AF7225]" : "bg-white border-slate-200"}`}
            >
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={(e) => setPicked({ ...picked, [opt.item]: e.target.checked })}
                  className="w-4 h-4 accent-[#AF7225]"
                />
                <span className="font-medium text-slate-800">{opt.label}</span>
              </div>
              <div className="flex gap-6 text-xs text-slate-500">
                <span>{aud(opt.estimated_cost)}</span>
                <span>+${opt.adr_lift_per_night}/night</span>
                <span>+{(opt.occupancy_lift * 100).toFixed(0)}% occ.</span>
              </div>
            </label>
          );
        })}
      </div>
      <div className="rounded-xl bg-slate-900 text-white p-5 space-y-3 text-sm">
        <div className="text-xs uppercase text-slate-400 tracking-wide">Cumulative impact</div>
        <Row label="Total cost" value={aud(totals.cost)} />
        <Row label="Annual revenue lift" value={aud(totals.revenueLift)} />
        <Row label="ROI (year 1)" value={pct(totals.roi, 1)} />
        <Row label="Payback" value={totals.paybackNights > 0 ? `${Math.round(totals.paybackNights)} nights (~${totals.paybackMonths.toFixed(1)} mo)` : "—"} />
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-300">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
