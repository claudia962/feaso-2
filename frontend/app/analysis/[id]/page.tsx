"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { AnalysisResponse, CompListResponse, RegulationResponse, PortfolioResponse } from "@/lib/types";
import { aud, pct, pctPoints } from "@/lib/format";
import { HeroCard } from "@/components/HeroCard";
import { MonthlyRevenueChart } from "@/components/MonthlyRevenueChart";
import { MCHistogram } from "@/components/MCHistogram";
import { StressPanel } from "@/components/StressPanel";
import { CompMap } from "@/components/CompMap";
import { ScenarioBuilder } from "@/components/ScenarioBuilder";
import { RenovationCalculator } from "@/components/RenovationCalculator";
import { PMCalculator } from "@/components/PMCalculator";
import { DownloadButtons } from "@/components/DownloadButtons";
import { Tabs } from "@/components/Tabs";

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [compList, setCompList] = useState<CompListResponse | null>(null);
  const [regulation, setRegulation] = useState<RegulationResponse | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    const fetchAll = async () => {
      try {
        const [a, c, r, p] = await Promise.allSettled([
          api.getAnalysis(id),
          api.getComps(id),
          api.getRegulation(id),
          api.getPortfolio(id),
        ]);
        if (cancelled) return;
        if (a.status === "fulfilled") setAnalysis(a.value);
        else setErr((a.reason as Error).message);
        if (c.status === "fulfilled") setCompList(c.value);
        if (r.status === "fulfilled") setRegulation(r.value);
        if (p.status === "fulfilled") setPortfolio(p.value);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    };
    fetchAll();
    const iv = setInterval(fetchAll, 8000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [id]);

  if (err) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-lg text-rose-700">
        {err}
      </div>
    );
  }
  if (!analysis) return <div className="text-slate-500">Loading analysis {id}…</div>;

  const subjectLat = (analysis as unknown as { latitude?: number | null }).latitude ?? null;
  const subjectLng = (analysis as unknown as { longitude?: number | null }).longitude ?? null;

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">← new analysis</Link>

      <HeroCard analysis={analysis} />

      <div className="flex justify-end">
        <DownloadButtons analysis={analysis} />
      </div>

      <Tabs tabs={[
        {
          id: "financials",
          label: "Financials",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-4">
              <h3 className="font-semibold text-slate-900">Monthly revenue projections</h3>
              <MonthlyRevenueChart projections={analysis.all_projections || (analysis.financials ? [analysis.financials] : [])} />
              <div className="grid md:grid-cols-3 gap-4 pt-4">
                {(analysis.all_projections || []).map((p) => (
                  <div key={p.projection_type} className="rounded-lg border border-slate-200 p-4">
                    <div className="text-xs uppercase text-slate-500 mb-2">{p.projection_type}</div>
                    <dl className="text-sm space-y-1">
                      <Row label="Y1 revenue" value={aud(p.year1_gross_revenue)} />
                      <Row label="NOI" value={aud(p.noi)} />
                      <Row label="Cap rate" value={pct(p.cap_rate ?? null, 2)} />
                      <Row label="Cash-on-cash" value={pct(p.cash_on_cash_return ?? null, 2)} />
                      <Row label="Break-even occ." value={pctPoints(p.break_even_occupancy ?? null)} />
                    </dl>
                  </div>
                ))}
              </div>
            </section>
          ),
        },
        {
          id: "monte_carlo",
          label: "Monte Carlo",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Revenue distribution (2,000 simulations)</h3>
              <MCHistogram analysis={analysis} />
            </section>
          ),
        },
        {
          id: "stress",
          label: "Stress tests",
          badge: analysis.stress_results?.length ?? undefined,
          content: (
            <section className="rounded-2xl bg-white shadow p-6">
              <h3 className="font-semibold text-slate-900 mb-4">Scenario resilience</h3>
              <StressPanel results={analysis.stress_results} />
            </section>
          ),
        },
        {
          id: "comps",
          label: "Comps",
          badge: compList?.count ?? analysis.comps?.length ?? undefined,
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-4">
              <h3 className="font-semibold text-slate-900">Comparable properties</h3>
              <CompMap subjectLat={subjectLat} subjectLng={subjectLng} comps={compList?.comps || []} />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                      <th className="text-left py-2">Comp</th>
                      <th className="text-right py-2">BR</th>
                      <th className="text-right py-2">ADR</th>
                      <th className="text-right py-2">Occupancy</th>
                      <th className="text-right py-2">Annual rev</th>
                      <th className="text-right py-2">Similarity</th>
                      <th className="text-right py-2">Dist.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(compList?.comps || analysis.comps || []).map((c, i) => (
                      <tr key={c.comp_listing_id || i} className="border-b border-slate-100">
                        <td className="py-2">{c.comp_name || c.comp_listing_id}</td>
                        <td className="py-2 text-right">{c.bedrooms ?? "—"}</td>
                        <td className="py-2 text-right">{c.avg_adr != null ? `$${Math.round(c.avg_adr)}` : "—"}</td>
                        <td className="py-2 text-right">{c.occupancy_rate != null ? `${(c.occupancy_rate * 100).toFixed(0)}%` : "—"}</td>
                        <td className="py-2 text-right">{aud(c.annual_revenue)}</td>
                        <td className="py-2 text-right">{c.similarity_score != null ? `${(c.similarity_score * 100).toFixed(0)}%` : "—"}</td>
                        <td className="py-2 text-right">{c.distance_km != null ? `${c.distance_km.toFixed(1)}km` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ),
        },
        {
          id: "regulation",
          label: "Regulation",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Regulatory assessment</h3>
              {regulation ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <Row label="Jurisdiction" value={regulation.municipality} />
                  <Row label="STR allowed" value={regulation.str_allowed ? "yes" : "no"} />
                  <Row label="Permit required" value={regulation.permit_required ? "yes" : "no"} />
                  <Row label="Max nights/year" value={regulation.max_nights_per_year != null ? String(regulation.max_nights_per_year) : "uncapped"} />
                  <Row label="Risk score" value={regulation.regulation_risk_score != null ? `${regulation.regulation_risk_score}/100` : "—"} />
                  <Row label="Last verified" value={regulation.last_verified ? regulation.last_verified.slice(0, 10) : "—"} />
                  <div className="col-span-2 text-slate-600 text-xs border-t border-slate-100 pt-2 mt-2">
                    {regulation.notes}
                  </div>
                </dl>
              ) : (
                <div className="text-slate-500 text-sm">Regulation data not yet recorded.</div>
              )}
            </section>
          ),
        },
        {
          id: "neighbourhood",
          label: "Neighbourhood",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Neighbourhood scoring</h3>
              {analysis.neighborhood ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <Row label="Walk score" value={analysis.neighborhood.walk_score?.toString() ?? "—"} />
                  <Row label="Transit score" value={analysis.neighborhood.transit_score?.toString() ?? "—"} />
                  <Row label="Bike score" value={analysis.neighborhood.bike_score?.toString() ?? "—"} />
                  <Row label="Nearest airport" value={analysis.neighborhood.nearest_airport_name ? `${analysis.neighborhood.nearest_airport_name} (${(analysis.neighborhood.nearest_airport_km ?? 0).toFixed(1)}km)` : "—"} />
                  <Row label="Nearest downtown" value={analysis.neighborhood.nearest_downtown_km != null ? `${(analysis.neighborhood.nearest_downtown_km).toFixed(1)}km` : "—"} />
                  <Row label="Restaurants (1km)" value={analysis.neighborhood.restaurants_within_1km?.toString() ?? "—"} />
                  <Row label="Best for" value={(analysis.neighborhood.best_for || []).join(", ") || "—"} />
                </dl>
              ) : (
                <div className="text-slate-500 text-sm">Neighbourhood data pending.</div>
              )}
            </section>
          ),
        },
        {
          id: "scenario",
          label: "Scenario",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">What-if explorer</h3>
              <p className="text-xs text-slate-500">Slide to see live-updating financials. For canonical stress tests, see the Stress tab.</p>
              <ScenarioBuilder base={analysis.financials} />
            </section>
          ),
        },
        {
          id: "renovations",
          label: "Renovations",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Renovation calculator</h3>
              <RenovationCalculator
                baseAdr={(analysis.financials?.monthly_projections?.[0]?.adr) || 220}
                baseOccupancy={(analysis.financials?.monthly_projections?.[0]?.occupancy) || 0.65}
              />
            </section>
          ),
        },
        {
          id: "portfolio",
          label: "Portfolio",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Portfolio fit</h3>
              {portfolio ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <Row label="Existing properties" value={String(portfolio.existing_property_count)} />
                  <Row label="Fit score" value={portfolio.overall_score != null ? `${portfolio.overall_score}/100` : "—"} />
                  <div className="col-span-2 text-slate-600 text-xs border-t border-slate-100 pt-2 mt-2">
                    {portfolio.recommendation}
                  </div>
                </dl>
              ) : (
                <div className="text-slate-500 text-sm">Portfolio fit not yet computed.</div>
              )}
            </section>
          ),
        },
        {
          id: "pm-calculator",
          label: "PM Calculator",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">LiveLuxe Hybrid PM Calculator</h3>
              <PMCalculator grossRevenue={analysis.financials?.year1_gross_revenue} />
            </section>
          ),
        },
        {
          id: "events",
          label: "Events",
          content: (
            <section className="rounded-2xl bg-white shadow p-6 space-y-3">
              <h3 className="font-semibold text-slate-900">Event impact</h3>
              {analysis.metadata?.event_impact ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <Row label="Events within radius" value={String(analysis.metadata.event_impact.events_within_radius ?? 0)} />
                  <Row label="Total event nights" value={String(analysis.metadata.event_impact.total_event_nights ?? 0)} />
                  <Row label="Annual revenue contribution" value={aud(analysis.metadata.event_impact.annual_revenue_contribution)} />
                  <div className="col-span-2 text-slate-600 text-xs border-t border-slate-100 pt-2 mt-2">
                    {analysis.metadata.event_impact.comparison}
                  </div>
                </dl>
              ) : (
                <div className="text-slate-500 text-sm">No event data captured.</div>
              )}
            </section>
          ),
        },
      ]} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{value}</span>
    </div>
  );
}
