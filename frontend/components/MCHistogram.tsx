"use client";

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AnalysisResponse } from "@/lib/types";

export function MCHistogram({ analysis }: { analysis: AnalysisResponse }) {
  const mc = analysis.metadata?.monte_carlo;
  const bins = mc?.histogram_bins;
  const counts = mc?.histogram_counts;
  const base = analysis.financials;

  if (!bins || !counts || bins.length < 2) {
    return <div className="text-slate-500 text-sm">Monte Carlo histogram not yet available.</div>;
  }

  // Pair bin edges with counts. bins.length == counts.length + 1 (standard histogram layout).
  const data = counts.map((count, i) => ({
    binLabel: `$${Math.round(bins[i] / 1000)}k`,
    bin: bins[i],
    count,
  }));

  const p50 = base?.mc_revenue_p50 ?? null;
  const p10 = base?.mc_revenue_p10 ?? null;
  const p90 = base?.mc_revenue_p90 ?? null;

  return (
    <div className="space-y-3">
      <div className="flex gap-6 text-xs text-slate-600">
        <Stat label="P10" value={p10} accent="text-rose-600" />
        <Stat label="P50 (median)" value={p50} accent="text-slate-900 font-semibold" />
        <Stat label="P90" value={p90} accent="text-emerald-600" />
        {mc?.probability_of_loss !== undefined && (
          <Stat
            label="Probability of loss"
            textValue={`${(mc.probability_of_loss * 100).toFixed(1)}%`}
            accent={mc.probability_of_loss > 0.2 ? "text-rose-600" : "text-emerald-600"}
          />
        )}
      </div>
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="binLabel" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8 }}
              labelStyle={{ color: "#fff", fontWeight: 600 }}
              itemStyle={{ color: "#fff" }}
            />
            <Bar dataKey="count" fill="#AF7225">
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    p50 != null && entry.bin > p50 + (p90 ?? 0) * 0.05
                      ? "#10b981"
                      : p50 != null && entry.bin < p50 - ((p50 - (p10 ?? 0)) * 0.5)
                      ? "#dc2626"
                      : "#AF7225"
                  }
                />
              ))}
            </Bar>
            {p50 != null && <ReferenceLine x={`$${Math.round(p50 / 1000)}k`} stroke="#0f172a" strokeDasharray="4 4" />}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({
  label, value, textValue, accent,
}: { label: string; value?: number | null; textValue?: string; accent: string }) {
  return (
    <div>
      <div className="uppercase text-[10px] text-slate-500 tracking-wide">{label}</div>
      <div className={`text-sm ${accent}`}>
        {textValue ?? (value != null ? `$${Math.round(value).toLocaleString()}` : "—")}
      </div>
    </div>
  );
}
