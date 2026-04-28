"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FinancialResponse } from "@/lib/types";

export function MonthlyRevenueChart({
  projections,
}: {
  projections?: FinancialResponse[];
}) {
  if (!projections || projections.length === 0) {
    return <div className="text-slate-500 text-sm">Monthly projections not yet available.</div>;
  }

  const base = projections.find((p) => p.projection_type === "base");
  const optimistic = projections.find((p) => p.projection_type === "optimistic");
  const pessimistic = projections.find((p) => p.projection_type === "pessimistic");

  const months = base?.monthly_projections || [];
  const data = months.map((row, i) => ({
    month: row.month.toUpperCase(),
    base: Math.round(row.revenue),
    optimistic: optimistic?.monthly_projections?.[i]?.revenue ?? null,
    pessimistic: pessimistic?.monthly_projections?.[i]?.revenue ?? null,
    occupancy: Math.round(row.occupancy * 100),
  }));

  return (
    <div className="h-[340px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <defs>
            <linearGradient id="band" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#AF7225" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#AF7225" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
          />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8 }}
            labelStyle={{ color: "#fff", fontWeight: 600 }}
            itemStyle={{ color: "#fff" }}
            formatter={(value) => `$${Number(value).toLocaleString()}`}
          />
          <Area
            type="monotone" dataKey="optimistic"
            stroke="#10b981" strokeWidth={1.5}
            fill="url(#band)" fillOpacity={0.35}
            name="Optimistic (P75)"
          />
          <Area
            type="monotone" dataKey="base"
            stroke="#AF7225" strokeWidth={2.5}
            fill="url(#band)" fillOpacity={0.5}
            name="Base (median)"
          />
          <Area
            type="monotone" dataKey="pessimistic"
            stroke="#dc2626" strokeWidth={1.5}
            fill="none"
            name="Pessimistic (P25)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
