"use client";

import jsPDF from "jspdf";
import Papa from "papaparse";
import { AnalysisResponse } from "@/lib/types";
import { API_BASE } from "@/lib/api";

export function DownloadButtons({ analysis }: { analysis: AnalysisResponse }) {
  const handleServerPdf = () => {
    window.open(`${API_BASE}/api/reports/${analysis.id}.pdf`, "_blank");
  };

  const handleClientPdf = () => {
    const doc = new jsPDF({ unit: "pt" });
    let y = 40;
    doc.setFontSize(16);
    doc.text("STR Feasibility Report", 40, y); y += 24;
    doc.setFontSize(10);
    doc.text(analysis.address, 40, y); y += 20;
    doc.text(`Score: ${analysis.overall_feasibility_score ?? "—"}/100`, 40, y); y += 16;
    doc.text(`Recommendation: ${analysis.recommendation ?? "—"}`, 40, y); y += 24;
    if (analysis.financials) {
      doc.text(`Year 1 revenue: $${Math.round(analysis.financials.year1_gross_revenue ?? 0).toLocaleString()}`, 40, y); y += 16;
      doc.text(`NOI: $${Math.round(analysis.financials.noi ?? 0).toLocaleString()}`, 40, y); y += 16;
      doc.text(`Cap rate: ${((analysis.financials.cap_rate ?? 0) * 100).toFixed(2)}%`, 40, y); y += 16;
      doc.text(`Cash-on-cash: ${((analysis.financials.cash_on_cash_return ?? 0) * 100).toFixed(2)}%`, 40, y); y += 24;
    }
    doc.setFont("helvetica", "italic");
    doc.text("Full rich report available via the PDF (server) button.", 40, y);
    doc.save(`feaso-${analysis.id.slice(0, 8)}.pdf`);
  };

  const handleCsv = () => {
    const rows: Record<string, unknown>[] = [];
    if (analysis.financials?.monthly_projections) {
      for (const mp of analysis.financials.monthly_projections) {
        rows.push({
          analysis_id: analysis.id,
          address: analysis.address,
          month: mp.month,
          adr: mp.adr,
          occupancy: mp.occupancy,
          revenue: mp.revenue,
          occupied_nights: mp.occupied_nights,
        });
      }
    }
    if (analysis.comps) {
      for (const c of analysis.comps) {
        rows.push({
          analysis_id: analysis.id,
          row_type: "comp",
          comp_id: c.comp_listing_id,
          name: c.comp_name,
          bedrooms: c.bedrooms,
          avg_adr: c.avg_adr,
          occupancy_rate: c.occupancy_rate,
          annual_revenue: c.annual_revenue,
          similarity_score: c.similarity_score,
          distance_km: c.distance_km,
        });
      }
    }
    const csv = Papa.unparse(rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feaso-${analysis.id.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/analysis/${analysis.id}`;
    try {
      await navigator.clipboard.writeText(url);
      alert(`Share link copied:\n${url}`);
    } catch {
      prompt("Copy the share URL:", url);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <button onClick={handleServerPdf}
        className="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800">
        PDF (full report)
      </button>
      <button onClick={handleClientPdf}
        className="px-4 py-2 rounded-lg bg-slate-100 text-slate-800 text-sm font-medium hover:bg-slate-200">
        PDF (quick)
      </button>
      <button onClick={handleCsv}
        className="px-4 py-2 rounded-lg bg-slate-100 text-slate-800 text-sm font-medium hover:bg-slate-200">
        CSV
      </button>
      <button onClick={handleShare}
        className="px-4 py-2 rounded-lg bg-[#AF7225] text-white text-sm font-medium hover:bg-[#8f5d1e]">
        Copy share link
      </button>
    </div>
  );
}
