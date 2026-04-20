"""
Report generator for STR feasibility analyses.

Produces three artefacts from a FeasibilityAnalysis ORM row:
  1. Markdown string  (always)
  2. HTML string      (always; feeds WeasyPrint)
  3. PDF bytes        (optional -- requires weasyprint; returns None when absent)

Never raises on missing data; sections fall back to "not available" so the
output is always complete. Exposes both the new `generate_report()` API and a
thin `ReportGenerator` class for backward-compat with earlier routes.
"""
from __future__ import annotations

import os
import tempfile as _tmpmod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog

from app.services.rag_engine import query_methodology

logger = structlog.get_logger(__name__)

_local_reports = Path(__file__).parent.parent.parent / "reports"
if os.environ.get("VERCEL") or not os.access(str(_local_reports.parent), os.W_OK):
    REPORTS_DIR = Path(_tmpmod.gettempdir()) / "feasibility_reports"
else:
    REPORTS_DIR = _local_reports
REPORTS_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class ReportBundle:
    markdown: str
    html: str
    pdf_bytes: Optional[bytes] = None


def generate_report(analysis: Any, *, pdf: bool = True) -> ReportBundle:
    """Build markdown + HTML (+ optional PDF) for the analysis."""
    md = _build_markdown(analysis)
    html = _build_html(md, analysis)
    pdf_bytes: Optional[bytes] = None
    if pdf:
        pdf_bytes = _render_pdf(html)
    return ReportBundle(markdown=md, html=html, pdf_bytes=pdf_bytes)


def calculate_score(data: dict) -> tuple[float, str]:
    """
    Score a dict of analysis inputs. Compat shim for the legacy
    test_report_generator.py expectations.

    Inputs (all optional, sensible defaults):
      cap_rate, regulation_risk_score, avg_occupancy, supply_growth_pct_12mo,
      neighborhood_score, probability_of_loss.
    """
    cap_rate = float(data.get("cap_rate") or 0)
    reg_risk = float(data.get("regulation_risk_score") or 50)
    occ = float(data.get("avg_occupancy") or 0)
    supply = float(data.get("supply_growth_pct_12mo") or 0)
    nbhd = float(data.get("neighborhood_score") or 50)
    ploss = float(data.get("probability_of_loss") or 0.3)

    cap_pts = min(30.0, max(-10.0, cap_rate * 300.0))             # 10% cap → 30 pts
    occ_pts = min(20.0, max(0.0, occ) * 20.0)                     # 100% occ → 20 pts
    reg_pts = max(0.0, (100.0 - reg_risk) * 0.18)                 # permissive → 18 pts
    nbhd_pts = max(0.0, nbhd * 0.15)                              # 100 → 15 pts
    supply_pts = max(0.0, 10.0 - supply)                          # low supply growth → 10 pts
    loss_pts = max(0.0, (1.0 - ploss) * 10.0)                     # low risk of loss → 10 pts

    total = cap_pts + occ_pts + reg_pts + nbhd_pts + supply_pts + loss_pts
    score = max(0.0, min(100.0, total))

    if score >= 75:
        rec = "strong_buy"
    elif score >= 60:
        rec = "buy"
    elif score >= 45:
        rec = "hold"
    elif score >= 30:
        rec = "avoid"
    else:
        rec = "strong_avoid"
    return round(score, 2), rec


class ReportGenerator:
    """Compat shim for the older API used by earlier routes."""

    def generate_overall_score(self, data: dict) -> tuple[float, str]:
        return calculate_score(data)

    def generate_markdown(self, analysis_id: str, data: dict) -> str:
        """
        Dict-based markdown render. Lightweight — sufficient for tests + smoke
        use. For the canonical ORM-backed report, call generate_report(analysis).
        """
        addr = data.get("address", "Unknown")
        created = data.get("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        score, rec = calculate_score(data)
        parts: list[str] = []
        parts.append(f"# Feasibility Report -- {addr}")
        parts.append(f"_Analysis ID: `{analysis_id}` | Generated: {created}_")
        parts.append("")
        parts.append("## 1. Executive Summary")
        parts.append(f"**Score:** {score:.0f} / 100 -- **{rec.replace('_', ' ').upper()}**")
        parts.append(f"- Gross revenue: {_money(data.get('gross_revenue'))}")
        parts.append(f"- NOI: {_money(data.get('noi'))}")
        parts.append(f"- Cap rate: {_pct(data.get('cap_rate'), 2)}")
        parts.append(f"- Cash-on-cash: {_pct(data.get('cash_on_cash_return'), 2)}")
        parts.append(f"- Break-even occupancy: {_pct(data.get('break_even_occupancy'), 1)}")
        parts.append("")
        parts.append("## 2. Comparable Analysis")
        comps = data.get("comps") or []
        parts.append(f"Comps: {len(comps)} records" if comps else "_No comparable properties supplied._")
        parts.append("")
        parts.append("## 3. Regulatory Risk")
        parts.append(f"- STR allowed: **{data.get('str_allowed')}**")
        parts.append(f"- Regulation risk score: **{data.get('regulation_risk_score')}/100**")
        parts.append("")
        parts.append("## 4. Neighbourhood")
        parts.append(f"- Walk Score: **{data.get('walk_score')}**")
        parts.append(f"- Nearest airport: **{data.get('nearest_airport_km')} km**")
        parts.append(f"- Nearest downtown: **{data.get('nearest_downtown_km')} km**")
        parts.append(f"- Best for: {', '.join(data.get('best_for') or []) or '-'}")
        parts.append(f"- Neighbourhood score: **{data.get('neighborhood_score')}/100**")
        parts.append("")
        parts.append("## 5. Financial Projections")
        parts.append(f"- Average ADR: {_money(data.get('avg_adr'))}")
        parts.append(f"- Average occupancy: {_pct(data.get('avg_occupancy'), 1)}")
        parts.append("")
        parts.append("### Monte Carlo")
        parts.append(f"- P10 revenue: {_money(data.get('mc_revenue_p10'))}")
        parts.append(f"- P50 revenue: {_money(data.get('mc_revenue_p50'))}")
        parts.append(f"- P90 revenue: {_money(data.get('mc_revenue_p90'))}")
        parts.append(f"- Probability of loss: {_pct(data.get('probability_of_loss'), 1)}")
        parts.append("")
        parts.append("## 6. Stress Tests")
        st = data.get("stress_tests") or []
        parts.append(f"{len(st)} scenarios recorded." if st else "_No stress tests supplied._")
        parts.append("")
        parts.append("## 7. Event Calendar")
        parts.append("_No event data supplied._")
        parts.append("")
        parts.append("## 8. Portfolio Fit")
        parts.append("_Portfolio fit not computed in legacy dict mode._")
        parts.append("")
        parts.append("## 9. Renovation Opportunities")
        renos = data.get("renovations") or []
        parts.append(f"{len(renos)} opportunities." if renos else "_No renovation analysis supplied._")
        parts.append("")
        parts.append("## 10. Exit Strategies")
        exits = data.get("exit_strategies") or []
        parts.append(f"{len(exits)} exit strategies." if exits else "_No exit modelling supplied._")
        parts.append("")
        parts.append("## 11. Supply Pipeline")
        parts.append(f"- Supply growth (12mo): **{data.get('supply_growth_pct_12mo')}%**")
        parts.append(f"- New listings (12mo): **{data.get('new_listings_last_12mo')}**")
        parts.append("")
        parts.append("---")
        parts.append("_Generated via ReportGenerator compat shim._")
        return "\n".join(parts)

    async def generate_pdf(self, analysis_id: str, db: Any) -> str:
        from sqlalchemy import select, update
        from sqlalchemy.orm import selectinload
        from app.models.database_models import FeasibilityAnalysis

        q = (
            select(FeasibilityAnalysis)
            .options(
                selectinload(FeasibilityAnalysis.comp_analyses),
                selectinload(FeasibilityAnalysis.financial_projections),
                selectinload(FeasibilityAnalysis.stress_tests),
                selectinload(FeasibilityAnalysis.neighborhood_scores),
                selectinload(FeasibilityAnalysis.regulation_assessments),
                selectinload(FeasibilityAnalysis.renovation_analyses),
                selectinload(FeasibilityAnalysis.exit_strategies),
                selectinload(FeasibilityAnalysis.portfolio_fit),
                selectinload(FeasibilityAnalysis.supply_pipeline),
            )
            .where(FeasibilityAnalysis.id == analysis_id)
        )
        row = (await db.execute(q)).scalar_one_or_none()
        if not row:
            raise ValueError(f"Analysis {analysis_id} not found")

        bundle = generate_report(row, pdf=True)
        suffix = "pdf" if bundle.pdf_bytes else "html"
        out_path = REPORTS_DIR / f"feaso-{analysis_id}.{suffix}"
        if bundle.pdf_bytes:
            out_path.write_bytes(bundle.pdf_bytes)
        else:
            out_path.write_text(bundle.html, encoding="utf-8")

        await db.execute(
            update(FeasibilityAnalysis)
            .where(FeasibilityAnalysis.id == analysis_id)
            .values(report_content=bundle.markdown, report_pdf_path=str(out_path))
        )
        await db.commit()
        return str(out_path)


def _build_markdown(a: Any) -> str:
    parts: list[str] = []

    parts.append(f"# Feasibility Report -- {a.address}")
    parts.append("")
    parts.append(f"_Analysis ID: `{a.id}` | Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    parts.append("")
    parts.append("## 1. Executive Summary")
    parts.append("")
    score = float(a.overall_feasibility_score) if a.overall_feasibility_score is not None else 0.0
    risk = float(a.risk_score) if a.risk_score is not None else 0.0
    rec = (a.recommendation or "pending").replace("_", " ").upper()
    traffic = "GREEN" if score >= 60 else ("AMBER" if score >= 45 else "RED")
    parts.append(f"**Score:** [{traffic}] **{score:.0f} / 100** -- **{rec}**  ")
    parts.append(f"**Risk score:** {risk:.0f} / 100  ")
    if a.recommendation_reasoning:
        parts.append("")
        parts.append(f"**Reasoning:** {a.recommendation_reasoning}")
    parts.append("")

    base_fp = _base_projection(a)
    if base_fp:
        parts.append("**Key metrics:**")
        parts.append(f"- Year 1 revenue: **{_money(base_fp.year1_gross_revenue)}**")
        parts.append(f"- NOI: **{_money(base_fp.noi)}**")
        parts.append(f"- Cap rate: **{_pct(base_fp.cap_rate, 2)}**")
        parts.append(f"- Cash-on-cash: **{_pct(base_fp.cash_on_cash_return, 2)}**")
        if base_fp.break_even_occupancy is not None:
            parts.append(f"- Break-even occupancy: **{float(base_fp.break_even_occupancy):.1f}%**")
    parts.append("")

    parts.append("## 2. Comparable Analysis")
    parts.append("")
    comps = list(getattr(a, "comp_analyses", None) or [])
    if comps:
        parts.append(f"Using **{len(comps)} comparable properties** ranked by weighted similarity.")
        parts.append("")
        parts.append("| # | Comp | BR | ADR | Occ. | Annual rev | Similarity | Dist |")
        parts.append("|---|------|----|-----|------|------------|------------|------|")
        for i, c in enumerate(sorted(comps, key=lambda c: float(c.similarity_score or 0), reverse=True)[:10], 1):
            parts.append(
                f"| {i} | {c.comp_name or c.comp_listing_id or '-'} "
                f"| {c.bedrooms or '-'} "
                f"| {_money(c.avg_adr)} "
                f"| {_pct(c.occupancy_rate, 0)} "
                f"| {_money(c.annual_revenue)} "
                f"| {_pct(c.similarity_score, 0)} "
                f"| {_float(c.distance_km, '-', ' km')} |"
            )
    else:
        parts.append("_No comparable properties recorded for this analysis._")
    parts.append("")

    parts.append("## 3. Regulatory Risk")
    parts.append("")
    regs = list(getattr(a, "regulation_assessments", None) or [])
    if regs:
        r = regs[0]
        indicator = "[ALLOWED]" if r.str_allowed else "[NOT PERMITTED]"
        parts.append(f"**{indicator}** in {r.municipality or '-'}.  ")
        parts.append(f"- Permit required: **{'yes' if r.permit_required else 'no'}**")
        cap = r.max_nights_per_year
        parts.append(f"- Night cap: **{cap if cap is not None else 'uncapped'}**")
        parts.append(f"- Regulation risk score: **{_float(r.regulation_risk_score)}/100**")
        if r.last_verified:
            parts.append(f"- Last verified: **{r.last_verified.date().isoformat()}**")
        if r.notes:
            parts.append("")
            parts.append(r.notes)
    else:
        parts.append("_No regulation assessment recorded._")
    parts.append("")

    parts.append("## 4. Neighbourhood")
    parts.append("")
    nbhds = list(getattr(a, "neighborhood_scores", None) or [])
    if nbhds:
        n = nbhds[0]
        parts.append(f"- Walk Score: **{n.walk_score or '-'}**")
        parts.append(f"- Transit Score: **{n.transit_score or '-'}**")
        parts.append(f"- Bike Score: **{n.bike_score or '-'}**")
        if n.nearest_airport_name:
            parts.append(f"- Nearest airport: **{n.nearest_airport_name}** ({_float(n.nearest_airport_km, '-', ' km')})")
        if n.nearest_downtown_km is not None:
            parts.append(f"- Nearest downtown: **{_float(n.nearest_downtown_km, '-', ' km')}**")
        if n.best_for:
            parts.append(f"- Best for: {', '.join(n.best_for)}")
        if n.neighborhood_score is not None:
            parts.append(f"- Composite score: **{_float(n.neighborhood_score)}/100**")
    else:
        parts.append("_Neighbourhood data not yet captured._")
    parts.append("")

    parts.append("## 5. Financial Projections")
    parts.append("")
    projections = list(getattr(a, "financial_projections", None) or [])
    if projections:
        parts.append("### Scenario comparison")
        parts.append("")
        parts.append("| Scenario | Y1 revenue | NOI | Cap rate | CoC | Break-even occ. |")
        parts.append("|----------|-----------|-----|----------|-----|-----------------|")
        order = {"pessimistic": 0, "base": 1, "optimistic": 2}
        for p in sorted(projections, key=lambda p: order.get(p.projection_type, 3)):
            parts.append(
                f"| {p.projection_type} "
                f"| {_money(p.year1_gross_revenue)} "
                f"| {_money(p.noi)} "
                f"| {_pct(p.cap_rate, 2)} "
                f"| {_pct(p.cash_on_cash_return, 2)} "
                f"| {_float(p.break_even_occupancy, '-', '%')} |"
            )
        if base_fp and base_fp.monthly_projections:
            parts.append("")
            parts.append("### Monthly base projections")
            parts.append("")
            parts.append("| Month | ADR | Occupancy | Revenue |")
            parts.append("|-------|-----|-----------|---------|")
            for mp in base_fp.monthly_projections:
                parts.append(
                    f"| {str(mp.get('month','')).upper()} "
                    f"| ${float(mp.get('adr', 0)):.0f} "
                    f"| {float(mp.get('occupancy', 0)) * 100:.0f}% "
                    f"| ${float(mp.get('revenue', 0)):,.0f} |"
                )
        meta = getattr(a, "metadata_", None) or {}
        mc = meta.get("monte_carlo") if isinstance(meta, dict) else None
        if mc and base_fp:
            parts.append("")
            parts.append("### Monte Carlo (2,000 simulations)")
            parts.append("")
            parts.append(f"- P10 revenue: **{_money(base_fp.mc_revenue_p10)}**")
            parts.append(f"- P50 revenue: **{_money(base_fp.mc_revenue_p50)}**")
            parts.append(f"- P90 revenue: **{_money(base_fp.mc_revenue_p90)}**")
            pol = mc.get("probability_of_loss")
            if pol is not None:
                parts.append(f"- Probability of loss: **{float(pol) * 100:.1f}%**")
    else:
        parts.append("_No financial projections available._")
    parts.append("")

    parts.append("## 6. Stress Tests")
    parts.append("")
    stresses = list(getattr(a, "stress_tests", None) or [])
    if stresses:
        parts.append("| Scenario | Revenue impact | Profitable? | Adaptation |")
        parts.append("|----------|----------------|-------------|-----------|")
        for s in stresses:
            imp = f"{float(s.revenue_impact_pct):.1f}%" if s.revenue_impact_pct is not None else "-"
            prof = "yes" if s.still_profitable else "no"
            parts.append(f"| {s.scenario_name} | {imp} | {prof} | {s.adaptation_strategy or '-'} |")
    else:
        parts.append("_No stress tests recorded._")
    parts.append("")

    parts.append("## 7. Event Calendar")
    parts.append("")
    meta_all = getattr(a, "metadata_", None) or {}
    meta_ev = meta_all.get("event_impact") if isinstance(meta_all, dict) else None
    if meta_ev:
        parts.append(f"- Events within 10km: **{meta_ev.get('events_within_radius', 0)}**")
        parts.append(f"- Total event nights: **{meta_ev.get('total_event_nights', 0)}**")
        parts.append(f"- Annual revenue contribution: **{_money(meta_ev.get('annual_revenue_contribution'))}**")
        if meta_ev.get("comparison"):
            parts.append("")
            parts.append(f"_{meta_ev['comparison']}_")
    else:
        parts.append("_No event data captured._")
    parts.append("")

    parts.append("## 8. Portfolio Fit")
    parts.append("")
    pf_rows = list(getattr(a, "portfolio_fit", None) or [])
    if pf_rows:
        pf = pf_rows[0]
        parts.append(f"- Existing property count: **{pf.existing_property_count or 0}**")
        if pf.overall_portfolio_fit_score is not None:
            parts.append(f"- Overall fit score: **{_float(pf.overall_portfolio_fit_score)}/100**")
        if pf.recommendation:
            parts.append("")
            parts.append(pf.recommendation)
    else:
        parts.append("_Portfolio fit not computed._")
    parts.append("")

    parts.append("## 9. Renovation Opportunities")
    parts.append("")
    renos = list(getattr(a, "renovation_analyses", None) or [])
    if renos:
        parts.append("| Item | Cost | ROI 1y | Recommendation |")
        parts.append("|------|------|--------|----------------|")
        for r in renos:
            parts.append(
                f"| {r.renovation_item} | {_money(r.estimated_cost)} "
                f"| {_pct(r.roi_1yr_pct, 1)} | {r.recommendation or '-'} |"
            )
    else:
        parts.append("_No renovation analysis computed._")
    parts.append("")

    parts.append("## 10. Exit Strategies")
    parts.append("")
    exits = list(getattr(a, "exit_strategies", None) or [])
    if exits:
        parts.append("| Strategy | Monthly income | Annual return | Notes |")
        parts.append("|----------|----------------|---------------|-------|")
        for e in exits:
            parts.append(
                f"| {e.strategy_type} | {_money(e.estimated_monthly_income)} "
                f"| {_pct(e.estimated_annual_return, 2)} | {e.notes or '-'} |"
            )
    else:
        parts.append("_Exit strategy modelling not run._")
    parts.append("")

    parts.append("## 11. Methodology & Sources")
    parts.append("")
    parts.append("**Data sources:** AirDNA, shared `events` table, Walk Score API, `regulations.json`.")
    parts.append("")
    parts.append("**Key assumptions:** 0.35 bedrooms + 0.25 type + 0.20 distance + 0.20 quality similarity, "
                 "Monte Carlo samples from comp distribution, regulation check runs first.")
    parts.append("")

    rag = query_methodology("feasibility scoring and comp analysis")
    if rag.available and rag.citations:
        parts.append("**Citations:**")
        for c in rag.citations:
            snippet = c.chunk_text[:200].strip()
            parts.append(f"- *{c.source_name}* -- {snippet} (sim {c.similarity:.2f})")
    else:
        parts.append(f"_{rag.note or 'RAG citations not yet populated.'}_")

    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(f"_Generated by feaso-2 at {datetime.now(timezone.utc).isoformat(timespec='minutes')}._")

    return "\n".join(parts)


def _build_html(md: str, a: Any) -> str:
    try:
        import markdown2
        body = markdown2.markdown(md, extras=["tables", "fenced-code-blocks", "header-ids"])
    except Exception:
        body = f"<pre>{md}</pre>"

    title = f"Feasibility Report -- {getattr(a, 'address', 'Unknown')}"
    css = (
        "@page { size: A4; margin: 22mm 18mm; }"
        "body { font-family: Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.5; }"
        "h1 { color: #0F172A; border-bottom: 3px solid #AF7225; padding-bottom: 8px; }"
        "h2 { color: #0F172A; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-top: 28px; }"
        "h3 { color: #334155; }"
        "table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; }"
        "th, td { padding: 6px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }"
        "th { background: #f8fafc; font-weight: 600; color: #475569; }"
        "em { color: #64748b; }"
        "code { background: #f1f5f9; padding: 2px 5px; border-radius: 3px; font-size: 11px; }"
        "strong { color: #0F172A; }"
        "hr { border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }"
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{title}</title>\n<style>{css}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def _render_pdf(html: str) -> Optional[bytes]:
    try:
        from weasyprint import HTML  # type: ignore
        return HTML(string=html).write_pdf()  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("report.pdf_unavailable", error=str(exc)[:200])
        return None


def _base_projection(a: Any) -> Optional[Any]:
    for p in (getattr(a, "financial_projections", None) or []):
        if p.projection_type == "base":
            return p
    return None


def _money(v: Any, *, cents: bool = False) -> str:
    if v is None:
        return "-"
    try:
        return f"${float(v):,.{2 if cents else 0}f}"
    except (TypeError, ValueError):
        return "-"


def _pct(v: Any, decimals: int = 1) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"


def _float(v: Any, fallback: str = "-", suffix: str = "") -> str:
    if v is None:
        return fallback
    try:
        return f"{float(v):.1f}{suffix}"
    except (TypeError, ValueError):
        return fallback
