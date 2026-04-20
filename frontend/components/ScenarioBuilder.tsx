"use client";

import { useMemo, useState } from "react";
import { aud, pct } from "@/lib/format";
import { FinancialResponse } from "@/lib/types";

/**
 * Client-side what-if explorer. Takes the base projection and lets the user
 * slide demand / ADR / interest-rate / platform-fee and see the recalculated
 * revenue, NOI, and cash-on-cash live. No backend round-trip required.
 */
export function ScenarioBuilder({ base }: { base?: FinancialResponse | null }) {
  const [demand, setDemand] = useState(0);     // % change
  const [adr, setAdr] = useState(0);           // % change
  const [interest, setInterest] = useState(0); // percentage points
  const [platform, setPlatform] = useState(0); // percentage points

  const result = useMemo(() => {
    if (!base) return null;
    const revenue = (base.year1_gross_revenue || 0) * (1 + demand / 100) * (1 + adr / 100);
    const expenses = base.annual_expenses || {};
    const totalExpenses = Object.values(expenses).reduce<number>(
      (acc, v) => acc + (typeof v === "number" ? v : 0),
      0,
    );
    const mortgageAdjust = ((expenses.mortgage_annual as number) || 0) * (interest / 100);
    const platformAdjust = revenue * (platform / 100);
    const adjustedExpenses = totalExpenses + mortgageAdjust + platformAdjust;
    const noi = revenue - adjustedExpenses;
    const capRate = noi / 1; // ratio intentionally left as raw; UI renders %
    return {
      revenue,
      totalExpenses: adjustedExpenses,
      noi,
      cashOnCash: base.cash_on_cash_return != null
        ? (base.cash_on_cash_return as number) + (noi - (base.noi || 0)) / Math.max(1, base.noi || 1) * 0.1
        : null,
      delta: revenue - (base.year1_gross_revenue || 0),
    };
  }, [base, demand, adr, interest, platform]);

  if (!base) return <div className="text-slate-500 text-sm">Base projection not ready.</div>;

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <Slider label="Demand (occupancy) change" value={demand} set={setDemand} min={-50} max={50} unit="%" />
        <Slider label="ADR change" value={adr} set={setAdr} min={-30} max={30} unit="%" />
        <Slider label="Interest-rate change" value={interest} set={setInterest} min={-3} max={5} unit="pp" step={0.25} />
        <Slider label="Platform-fee change" value={platform} set={setPlatform} min={-2} max={10} unit="pp" step={0.5} />
      </div>
      <div className="rounded-xl bg-slate-50 p-5 space-y-3 text-sm">
        <Row label="Adjusted revenue" value={aud(result?.revenue)} delta={result?.delta} base={base.year1_gross_revenue} />
        <Row label="Adjusted expenses" value={aud(result?.totalExpenses)} />
        <Row label="Adjusted NOI" value={aud(result?.noi)} />
        <Row label="Cash-on-cash (est.)" value={pct(result?.cashOnCash ?? null)} />
        <hr className="border-slate-200" />
        <div className="text-xs text-slate-500">
          Adjustments are additive over the base case. For a canonical stress result, see the Stress tab.
        </div>
      </div>
    </div>
  );
}

function Slider({
  label, value, set, min, max, unit, step = 1,
}: {
  label: string; value: number; set: (v: number) => void;
  min: number; max: number; unit: string; step?: number;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-600 mb-1">
        <span>{label}</span>
        <span className="font-mono font-semibold text-slate-900">
          {value > 0 ? "+" : ""}{value}{unit}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => set(parseFloat(e.target.value))}
        className="w-full accent-[#AF7225]"
      />
    </div>
  );
}

function Row({
  label, value, delta, base,
}: { label: string; value: string; delta?: number; base?: number | null }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold text-slate-900">
        {value}
        {delta != null && base != null && (
          <span className={`ml-2 text-xs ${delta >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
            ({delta >= 0 ? "+" : ""}{((delta / Math.max(1, base)) * 100).toFixed(1)}%)
          </span>
        )}
      </span>
    </div>
  );
}
