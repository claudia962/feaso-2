"use client";

import { AnalysisResponse } from "@/lib/types";
import { aud, pct, recColor, recLabel } from "@/lib/format";

export function HeroCard({ analysis }: { analysis: AnalysisResponse }) {
  const score = analysis.overall_feasibility_score ?? 0;
  const risk = analysis.risk_score ?? 0;
  const base = analysis.financials;
  const regHalted =
    analysis.recommendation === "strong_avoid" &&
    analysis.recommendation_reasoning?.includes("STR BANNED");

  return (
    <section className="rounded-2xl bg-white shadow-lg overflow-hidden">
      {regHalted && (
        <div className="bg-rose-700 text-white px-6 py-3 font-semibold tracking-wide uppercase text-sm">
          ⚠ Regulatory block: STR not permitted (or heavily capped) in this jurisdiction.
          See regulation tab for details.
        </div>
      )}
      <div className="grid md:grid-cols-[auto,1fr,1fr] gap-8 p-8">
        <div className="flex flex-col items-center justify-center">
          <div className="relative w-40 h-40">
            <svg className="w-full h-full -rotate-90">
              <circle cx="80" cy="80" r="70" fill="none" stroke="#e2e8f0" strokeWidth="12" />
              <circle
                cx="80" cy="80" r="70" fill="none"
                stroke={score >= 60 ? "#059669" : score >= 45 ? "#d97706" : "#be123c"}
                strokeWidth="12"
                strokeDasharray={`${(score / 100) * 440} 440`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-4xl font-bold text-slate-900">{score.toFixed(0)}</div>
              <div className="text-xs uppercase text-slate-500 tracking-wide">out of 100</div>
            </div>
          </div>
          <div className={`mt-4 px-4 py-1.5 rounded-full text-white text-sm font-semibold ${recColor(analysis.recommendation)}`}>
            {recLabel(analysis.recommendation)}
          </div>
        </div>

        <div>
          <h2 className="text-xl font-semibold text-slate-900">{analysis.address}</h2>
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">
            {analysis.recommendation_reasoning || "Analysis in progress…"}
          </p>
          <dl className="grid grid-cols-2 gap-3 mt-6 text-sm">
            <div>
              <dt className="text-slate-500 uppercase text-xs">Year 1 revenue</dt>
              <dd className="font-semibold text-slate-900">{aud(base?.year1_gross_revenue)}</dd>
            </div>
            <div>
              <dt className="text-slate-500 uppercase text-xs">NOI</dt>
              <dd className="font-semibold text-slate-900">{aud(base?.noi)}</dd>
            </div>
            <div>
              <dt className="text-slate-500 uppercase text-xs">Cap rate</dt>
              <dd className="font-semibold text-slate-900">{pct(base?.cap_rate ?? null, 2)}</dd>
            </div>
            <div>
              <dt className="text-slate-500 uppercase text-xs">Cash-on-cash</dt>
              <dd className="font-semibold text-slate-900">{pct(base?.cash_on_cash_return ?? null, 2)}</dd>
            </div>
            <div>
              <dt className="text-slate-500 uppercase text-xs">Break-even occupancy</dt>
              <dd className="font-semibold text-slate-900">
                {base?.break_even_occupancy != null
                  ? `${(base.break_even_occupancy as number).toFixed(1)}%`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 uppercase text-xs">Risk score</dt>
              <dd className="font-semibold text-slate-900">{risk.toFixed(0)} / 100</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-col gap-2 text-xs">
          <div className="text-slate-500 uppercase">Pipeline progress</div>
          <ul className="space-y-1">
            {[
              "geocoded",
              "regulations",
              "neighbourhood",
              "comps",
              "financials",
              "monte_carlo",
              "stress_tests",
              "events",
              "portfolio_fit",
            ].map((step) => {
              const done = analysis.steps_complete?.includes(step);
              return (
                <li key={step} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${done ? "bg-emerald-500" : "bg-slate-300"}`} />
                  <span className={done ? "text-slate-700" : "text-slate-400"}>
                    {step.replace("_", " ")}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
