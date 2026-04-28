"use client";

import { useState } from "react";

const fmt = (n: number, prefix = "$") =>
  `${prefix}${Math.round(n).toLocaleString("en-AU")}`;

export function PMCalculator({ grossRevenue: initialGross }: { grossRevenue?: number | null }) {
  const defaultGross = initialGross ?? 58900;

  const [pm, setPm] = useState({
    grossRevenue: defaultGross.toString(),
    mgmtPct: "18",
    gst: true,
    platformPct: "15.5",
    cleaningCost: "120",
    cleaningsPerYear: "100",
    overPerfThreshold: Math.round(defaultGross * 0.85).toString(),
    overPerfBonusPct: "10",
    ltrWeekly: "650",
  });

  const calcPM = () => {
    const gross = parseFloat(pm.grossRevenue) || 0;
    const platFee = gross * (parseFloat(pm.platformPct) / 100);
    const mgmtFee = gross * (parseFloat(pm.mgmtPct) / 100);
    const gstAmt = pm.gst ? mgmtFee * 0.1 : 0;
    const cleaning = parseFloat(pm.cleaningCost) * parseFloat(pm.cleaningsPerYear);
    const threshold = parseFloat(pm.overPerfThreshold) || 0;
    const overPerf = gross > threshold ? (gross - threshold) * (parseFloat(pm.overPerfBonusPct) / 100) : 0;
    const netOwner = gross - platFee - mgmtFee - gstAmt - cleaning - overPerf;
    const ltrAnnual = parseFloat(pm.ltrWeekly) * 52;
    return { gross, platFee, mgmtFee, gstAmt, cleaning, overPerf, netOwner, ltrAnnual };
  };

  const c = calcPM();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Inputs */}
      <div className="space-y-4">
        <p className="text-xs text-slate-400">Adjust inputs to model different scenarios.</p>

        {[
          { key: "grossRevenue", label: "Gross STR Revenue (AUD)", type: "number" },
          { key: "mgmtPct", label: "Base Management Fee %", type: "number" },
          { key: "platformPct", label: "Platform Fee % (Airbnb)", type: "number" },
          { key: "cleaningCost", label: "Cleaning Cost per Turn ($)", type: "number" },
          { key: "cleaningsPerYear", label: "Est. Cleans per Year", type: "number" },
          { key: "overPerfThreshold", label: "Overperformance Threshold ($)", type: "number" },
          { key: "overPerfBonusPct", label: "Overperformance Bonus %", type: "number" },
          { key: "ltrWeekly", label: "LTR Comparison ($/week)", type: "number" },
        ].map((field) => (
          <div key={field.key}>
            <label className="block text-xs font-medium text-slate-600 mb-1">{field.label}</label>
            <input
              type={field.type}
              value={pm[field.key as keyof typeof pm] as string}
              onChange={(e) => setPm((prev) => ({ ...prev, [field.key]: e.target.value }))}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#AF7225]"
            />
          </div>
        ))}

        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-slate-600">GST on management fee</label>
          <button
            onClick={() => setPm((p) => ({ ...p, gst: !p.gst }))}
            className={`relative w-10 h-5 rounded-full transition-colors ${pm.gst ? "bg-[#AF7225]" : "bg-slate-300"}`}
          >
            <span
              className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${pm.gst ? "translate-x-5" : "translate-x-0.5"}`}
            />
          </button>
          <span className="text-xs text-slate-400">{pm.gst ? "Yes (+10%)" : "No"}</span>
        </div>
      </div>

      {/* Output */}
      <div className="space-y-4">
        {/* Net to owner — hero */}
        <div className="bg-[#0F172A] rounded-xl p-6 text-white text-center">
          <p className="text-sm text-slate-400 mb-1">Net to Owner</p>
          <p className="text-4xl font-bold text-[#AF7225]">{fmt(c.netOwner)}</p>
          <p className="text-sm text-slate-400 mt-1">per year</p>
          <p className="text-lg font-semibold mt-2">{fmt(c.netOwner / 52)}/week</p>
        </div>

        {/* Waterfall */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h3 className="text-sm font-semibold text-[#0F172A] mb-3">Fee Waterfall</h3>
          {[
            { label: "Gross STR Revenue", value: c.gross, type: "neutral" },
            { label: `Platform fees (${pm.platformPct}%)`, value: -c.platFee, type: "deduct" },
            { label: `LiveLuxe base fee (${pm.mgmtPct}%)`, value: -c.mgmtFee, type: "deduct" },
            ...(pm.gst ? [{ label: "GST on management fee", value: -c.gstAmt, type: "deduct" as const }] : []),
            { label: `Cleaning (${pm.cleaningsPerYear} × $${pm.cleaningCost})`, value: -c.cleaning, type: "deduct" },
            ...(c.overPerf > 0
              ? [{ label: `Overperformance bonus (${pm.overPerfBonusPct}% above threshold)`, value: -c.overPerf, type: "deduct" as const }]
              : []),
          ].map((row, i) => (
            <div
              key={i}
              className={`flex justify-between text-sm py-1.5 border-b border-slate-50 last:border-0 ${row.type === "deduct" ? "text-red-600" : "text-[#0F172A] font-medium"}`}
            >
              <span>{row.label}</span>
              <span>{row.value >= 0 ? fmt(row.value) : `−${fmt(Math.abs(row.value))}`}</span>
            </div>
          ))}
          <div className="flex justify-between text-sm font-bold pt-2 text-[#0F172A]">
            <span>NET TO OWNER</span>
            <span className="text-[#AF7225] text-base">{fmt(c.netOwner)}</span>
          </div>
        </div>

        {/* LTR comparison */}
        <div
          className={`rounded-xl p-4 text-sm ${c.netOwner > c.ltrAnnual ? "bg-green-50 border border-green-200" : "bg-amber-50 border border-amber-200"}`}
        >
          <div className="flex justify-between items-center">
            <span className="font-medium">vs Long-Term Rental</span>
            <span className={`font-bold ${c.netOwner > c.ltrAnnual ? "text-green-700" : "text-amber-700"}`}>
              {c.netOwner > c.ltrAnnual ? "+" : ""}
              {fmt(c.netOwner - c.ltrAnnual)}/yr
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            LTR at ${pm.ltrWeekly}/wk = {fmt(c.ltrAnnual)}/yr net. STR{" "}
            {c.netOwner > c.ltrAnnual ? "outperforms" : "underperforms"} by{" "}
            {fmt(Math.abs(c.netOwner - c.ltrAnnual))}/yr.
          </p>
        </div>

        <p className="text-xs text-slate-400 text-center">
          Estimate only · Does not include strata, council rates, insurance or income tax
        </p>
      </div>
    </div>
  );
}
