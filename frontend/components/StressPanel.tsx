"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { StressResult } from "@/lib/types";

export function StressPanel({ results }: { results?: StressResult[] }) {
  if (!results || results.length === 0) {
    return <div className="text-slate-500 text-sm">Stress tests not yet run.</div>;
  }

  const data = results.map((r) => ({
    name: r.scenario_name,
    impact: r.revenue_impact_pct != null ? Number(r.revenue_impact_pct) : 0,
    profitable: !!r.still_profitable,
  }));

  return (
    <div className="space-y-4">
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 40, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" stroke="#64748b" fontSize={11} angle={-15} textAnchor="end" height={60} />
            <YAxis
              stroke="#64748b" fontSize={12}
              tickFormatter={(v: number) => `${Number(v).toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8 }}
              formatter={(value) => `${Number(value).toFixed(1)}%`}
            />
            <Bar dataKey="impact">
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.profitable ? "#10b981" : "#dc2626"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-slate-500 border-b border-slate-200">
            <th className="py-2 text-left">Scenario</th>
            <th className="py-2 text-right">Revenue impact</th>
            <th className="py-2 text-right">Profitable?</th>
            <th className="py-2 text-left pl-4">Adaptation strategy</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.scenario_name} className="border-b border-slate-100">
              <td className="py-3 font-medium text-slate-800">{r.scenario_name}</td>
              <td className="py-3 text-right text-slate-700">
                {r.revenue_impact_pct != null ? `${Number(r.revenue_impact_pct).toFixed(1)}%` : "—"}
              </td>
              <td className="py-3 text-right">
                <span className={`text-xs px-2 py-0.5 rounded ${r.still_profitable ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                  {r.still_profitable ? "yes" : "no"}
                </span>
              </td>
              <td className="py-3 pl-4 text-slate-600 text-xs max-w-md">
                {r.adaptation_strategy || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
