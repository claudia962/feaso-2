"use client";

import { useRouter } from "next/navigation";
import { useState, FormEvent } from "react";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [form, setForm] = useState({
    address: "58 Jeffcott Street, West Melbourne VIC 3003",
    property_type: "apartment",
    bedrooms: 2,
    bathrooms: 2,
    purchase_price: 780_000,
    estimated_renovation: 0,
    down_payment_pct: 20,
    mortgage_rate_pct: 6.5,
    mortgage_term_years: 30,
  });

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm({ ...form, [key]: value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setSubmitting(true);
    try {
      const res = await api.createAnalysis(form);
      router.push(`/analysis/${res.id}`);
    } catch (error) {
      setErr(error instanceof Error ? error.message : String(error));
      setSubmitting(false);
    }
  };

  return (
    <div className="grid md:grid-cols-[1fr,400px] gap-10">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">STR Feasibility Analysis</h1>
        <p className="mt-3 text-slate-600 max-w-lg">
          Enter a prospective property below. We&apos;ll crunch comparable listings, regulatory risk,
          financial projections, Monte Carlo variance, stress tests, renovation ROI, and exit strategy
          — usually in 10-30 seconds.
        </p>
        <form onSubmit={submit} className="mt-8 space-y-5 max-w-xl">
          <Field label="Address">
            <input type="text" required value={form.address}
              onChange={(e) => set("address", e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Property type">
              <select value={form.property_type}
                onChange={(e) => set("property_type", e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none">
                {["apartment", "house", "townhouse", "cabin", "villa", "studio", "condo"].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </Field>
            <Field label="Bedrooms">
              <input type="number" min={0} max={20} value={form.bedrooms}
                onChange={(e) => set("bedrooms", parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Bathrooms">
              <input type="number" step={0.5} min={0} max={20} value={form.bathrooms}
                onChange={(e) => set("bathrooms", parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Purchase price">
              <input type="number" min={0} value={form.purchase_price}
                onChange={(e) => set("purchase_price", parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Renovation budget">
              <input type="number" min={0} value={form.estimated_renovation}
                onChange={(e) => set("estimated_renovation", parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Down payment %">
              <input type="number" min={0} max={100} value={form.down_payment_pct}
                onChange={(e) => set("down_payment_pct", parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Mortgage rate %">
              <input type="number" step={0.01} min={0} max={20} value={form.mortgage_rate_pct}
                onChange={(e) => set("mortgage_rate_pct", parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
            <Field label="Mortgage term (yrs)">
              <input type="number" min={1} max={40} value={form.mortgage_term_years}
                onChange={(e) => set("mortgage_term_years", parseInt(e.target.value) || 30)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-[#AF7225] outline-none" />
            </Field>
          </div>

          {err && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">
              {err}
            </div>
          )}

          <button type="submit" disabled={submitting}
            className="w-full md:w-auto px-8 py-3 rounded-xl bg-[#AF7225] text-white font-semibold hover:bg-[#8f5d1e] disabled:opacity-50 disabled:cursor-wait">
            {submitting ? "Analysing…" : "Run feasibility analysis"}
          </button>
        </form>
      </div>

      <aside className="bg-white rounded-2xl shadow p-6 self-start">
        <h3 className="font-semibold text-slate-900 mb-3">What you&apos;ll get</h3>
        <ul className="text-sm text-slate-600 space-y-2">
          <Li>Overall feasibility score + recommendation</Li>
          <Li>Comparable-property analysis (ranked by similarity)</Li>
          <Li>Regulation check (first line of defence)</Li>
          <Li>Monthly revenue projections with confidence bands</Li>
          <Li>Monte Carlo distribution (2,000 simulations)</Li>
          <Li>7 stress-test scenarios with adaptation plays</Li>
          <Li>Renovation ROI calculator</Li>
          <Li>Exit-strategy comparison</Li>
          <Li>PDF + CSV export</Li>
        </ul>
        <div className="mt-4 text-xs text-slate-400 border-t border-slate-100 pt-3">
          Demo keys fall back to mock data. Live keys unlock real AirDNA comps & Walk Score numbers.
        </div>
      </aside>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-slate-500 tracking-wide">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function Li({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-2">
      <span className="text-[#AF7225]">→</span>
      <span>{children}</span>
    </li>
  );
}
