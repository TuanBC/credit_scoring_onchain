"""JSON API routes for credit scoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import PlainTextResponse

from app.dependencies import (
    get_scoring_engine,
    require_report_service,
)
from app.schemas import ScoreResponse
from app.services.reporting import WalletReportService
from app.services.scoring_engine import ScoringEngine


router = APIRouter(tags=["Credit Scoring API"])


@router.get("/health")
async def health() -> dict:
    """Basic liveness probe."""
    return {"status": "healthy", "service": "credit-scoring-web"}


@router.get(
    "/v1/wallets/{wallet_address}/score",
    response_model=ScoreResponse,
    summary="Fetch credit score for a wallet",
)
async def get_wallet_score(
    wallet_address: str = Path(
        ..., description="Checksum or lowercase Ethereum address"
    ),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
) -> ScoreResponse:
    """Return the on-chain credit score for the requested wallet."""
    result = await scoring_engine.evaluate_wallet(wallet_address)
    return ScoreResponse(**result.as_payload())


@router.get(
    "/v1/wallets/{wallet_address}/report/markdown",
    response_class=PlainTextResponse,
    summary="Generate raw Markdown credit report",
)
async def get_wallet_report_markdown(
    wallet_address: str = Path(
        ..., description="Checksum or lowercase Ethereum address"
    ),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    report_service: WalletReportService = Depends(require_report_service),
) -> str:
    """Generate an LLM-backed markdown report for the wallet (raw markdown)."""
    result = await scoring_engine.evaluate_wallet(wallet_address)
    if not result.onchain_features:
        raise HTTPException(
            status_code=404,
            detail="Unable to generate report without transaction history",
        )
    return await report_service.generate_markdown_report(result)
