"""Reports endpoint — markdown / HTML / PDF / CSV feasibility reports."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_session
from app.models.database_models import FeasibilityAnalysis
from app.services.report_generator import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = structlog.get_logger(__name__)


async def _fetch_full(db: AsyncSession, analysis_id: UUID) -> FeasibilityAnalysis:
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
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return row


@router.get("/{analysis_id}.pdf")
@router.get("/{analysis_id}/pdf")
async def get_pdf(analysis_id: UUID, db: AsyncSession = Depends(get_session)):
    """
    Serve the PDF feasibility report. Falls back to HTML with `text/html`
    when WeasyPrint is not installed in the runtime (Vercel serverless).
    """
    analysis = await _fetch_full(db, analysis_id)
    bundle = generate_report(analysis, pdf=True)
    if bundle.pdf_bytes:
        headers = {"Content-Disposition": f'inline; filename="feaso-{analysis_id}.pdf"'}
        return Response(content=bundle.pdf_bytes, media_type="application/pdf", headers=headers)
    # Graceful fallback: serve HTML so browsers can Print → Save as PDF.
    logger.warning("reports.pdf_fallback_html", analysis_id=str(analysis_id))
    return HTMLResponse(content=bundle.html, status_code=200)


@router.get("/{analysis_id}.html")
@router.get("/{analysis_id}/html")
async def get_html(analysis_id: UUID, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    analysis = await _fetch_full(db, analysis_id)
    bundle = generate_report(analysis, pdf=False)
    return HTMLResponse(content=bundle.html)


@router.get("/{analysis_id}.md")
@router.get("/{analysis_id}/markdown")
async def get_markdown(analysis_id: UUID, db: AsyncSession = Depends(get_session)) -> PlainTextResponse:
    analysis = await _fetch_full(db, analysis_id)
    bundle = generate_report(analysis, pdf=False)
    # Persist markdown for later cheap retrieval.
    try:
        analysis.report_content = bundle.markdown
        await db.commit()
    except Exception:
        await db.rollback()
    return PlainTextResponse(content=bundle.markdown, media_type="text/markdown")


@router.get("/{analysis_id}.csv")
@router.get("/{analysis_id}/csv")
async def get_csv(analysis_id: UUID, db: AsyncSession = Depends(get_session)) -> StreamingResponse:
    """Flat CSV export: monthly projections + comps + stress results."""
    analysis = await _fetch_full(db, analysis_id)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["row_type", "key", "value"])
    w.writerow(["meta", "analysis_id", str(analysis.id)])
    w.writerow(["meta", "address", analysis.address])
    w.writerow(["meta", "overall_score", analysis.overall_feasibility_score])
    w.writerow(["meta", "risk_score", analysis.risk_score])
    w.writerow(["meta", "recommendation", analysis.recommendation])

    base_fp = next((p for p in analysis.financial_projections if p.projection_type == "base"), None)
    if base_fp and base_fp.monthly_projections:
        w.writerow([])
        w.writerow(["monthly", "month", "adr", "occupancy", "revenue", "occupied_nights"])
        for mp in base_fp.monthly_projections:
            w.writerow(["monthly", mp.get("month"), mp.get("adr"), mp.get("occupancy"),
                        mp.get("revenue"), mp.get("occupied_nights")])

    if analysis.comp_analyses:
        w.writerow([])
        w.writerow(["comp", "name", "bedrooms", "avg_adr", "occupancy_rate",
                    "annual_revenue", "similarity_score", "distance_km"])
        for c in analysis.comp_analyses:
            w.writerow(["comp", c.comp_name or c.comp_listing_id, c.bedrooms, c.avg_adr,
                        c.occupancy_rate, c.annual_revenue, c.similarity_score, c.distance_km])

    if analysis.stress_tests:
        w.writerow([])
        w.writerow(["stress", "scenario_name", "revenue_impact_pct", "still_profitable", "adaptation_strategy"])
        for s in analysis.stress_tests:
            w.writerow(["stress", s.scenario_name, s.revenue_impact_pct,
                        s.still_profitable, (s.adaptation_strategy or "").replace("\n", " ")])

    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="feaso-{analysis_id}.csv"'}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
