"""Server-rendered routes with Etherscan-inspired styling."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, Form, Path, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.dependencies import (
    get_rate_limiter,
    get_scoring_engine,
    report_generation_enabled,
    require_report_service,
)
from app.services.limiter import RateLimiter
from app.services.reporting import WalletReportService
from app.services.scoring_engine import ScoringEngine


settings = get_settings()
templates = Jinja2Templates(directory=str(settings.template_dir))
router = APIRouter(include_in_schema=False)


# Handle Chrome DevTools configuration request silently
@router.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config() -> Response:
    """Return empty response for Chrome DevTools config request."""
    return Response(status_code=204)


# Credit grade table for risk categorization
GRADE_TABLE = [
    {
        "grade": 1,
        "min_score": 700,
        "max_score": 1000,
        "risk_category": "Ultra Low Risk (A++)",
        "expected_bad_rate": 0.0,
    },
    {
        "grade": 2,
        "min_score": 653,
        "max_score": 699,
        "risk_category": "Very Low Risk (A+)",
        "expected_bad_rate": 1.7,
    },
    {
        "grade": 3,
        "min_score": 600,
        "max_score": 652,
        "risk_category": "Low Risk (A)",
        "expected_bad_rate": 2.7,
    },
    {
        "grade": 4,
        "min_score": 570,
        "max_score": 599,
        "risk_category": "Moderate Risk (B)",
        "expected_bad_rate": 4.6,
    },
    {
        "grade": 5,
        "min_score": 528,
        "max_score": 569,
        "risk_category": "High Risk (C)",
        "expected_bad_rate": 17.3,
    },
    {
        "grade": 6,
        "min_score": 0,
        "max_score": 527,
        "risk_category": "Very High Risk (C-)",
        "expected_bad_rate": 40.4,
    },
]


def get_grade_info(score: float) -> Dict[str, Any]:
    """Get grade information based on credit score."""
    for grade in GRADE_TABLE:
        if grade["min_score"] <= score <= grade["max_score"]:
            # Calculate meter position (0-100, where 100 is best)
            meter_percent = min(100, max(0, (score / 1000) * 100))
            return {
                **grade,
                "meter_percent": meter_percent,
            }
    # Default to lowest grade
    return {**GRADE_TABLE[-1], "meter_percent": 0}


def _template_context(
    request: Request,
    page_title: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base_ctx = {"request": request, "page_title": page_title}
    if extra:
        base_ctx.update(extra)
    return base_ctx


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Render the dashboard landing page."""
    return templates.TemplateResponse(
        "home.html",
        _template_context(
            request,
            page_title=settings.app_name,
            extra={"report_enabled": report_generation_enabled()},
        ),
    )


@router.post(
    "/scores",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_score_request(
    request: Request,
    wallet_address: str = Form(..., min_length=42, max_length=42),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> HTMLResponse:
    """Handle the address submission from the landing page."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Normalize address (ensure lowercase and proper format)
        wallet_address = wallet_address.strip().lower()
        if not wallet_address.startswith("0x"):
            wallet_address = "0x" + wallet_address

        # Validate length after normalization
        if len(wallet_address) != 42:
            return templates.TemplateResponse(
                "home.html",
                _template_context(
                    request,
                    page_title=settings.app_name,
                    extra={
                        "message": f"Invalid address length. Expected 42 characters, got {len(wallet_address)}.",
                        "report_enabled": report_generation_enabled(),
                    },
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        client_ip = request.client.host if request.client else "anonymous"
        logger.info(
            f"Score request from {client_ip} for wallet {wallet_address[:10]}..."
        )

        if not rate_limiter.allow(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return templates.TemplateResponse(
                "home.html",
                _template_context(
                    request,
                    page_title=settings.app_name,
                    extra={
                        "message": "Rate limit exceeded. Please retry in a moment.",
                        "report_enabled": report_generation_enabled(),
                    },
                ),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        result = await scoring_engine.evaluate_wallet(wallet_address)
        template_name = "score_detail.html" if result.onchain_features else "home.html"

        context = {
            "wallet_address": result.wallet_address,
            "score": result.credit_score,
            "features": result.onchain_features,
            "offchain": result.offchain_data,
            "time_series": result.time_series_data or {},
            "message": result.message,
            "report_enabled": report_generation_enabled(),
        }

        return templates.TemplateResponse(
            template_name,
            _template_context(
                request,
                page_title=f"Score for {result.wallet_address}",
                extra=context,
            ),
        )
    except Exception as e:
        # Log error and return user-friendly message
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error processing score request: {e}", exc_info=True)

        return templates.TemplateResponse(
            "home.html",
            _template_context(
                request,
                page_title=settings.app_name,
                extra={
                    "message": f"An error occurred: {str(e)}. Please try again.",
                    "report_enabled": report_generation_enabled(),
                },
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/api/v1/wallets/{wallet_address}/report",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
async def get_wallet_report_html(
    request: Request,
    wallet_address: str = Path(
        ..., description="Checksum or lowercase Ethereum address"
    ),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    report_service: WalletReportService = Depends(require_report_service),
) -> HTMLResponse:
    """Render the credit report as an HTML page."""
    try:
        # Normalize address
        wallet_address = wallet_address.strip().lower()
        if not wallet_address.startswith("0x"):
            wallet_address = "0x" + wallet_address

        # Get wallet score and features
        result = await scoring_engine.evaluate_wallet(wallet_address)

        if not result.onchain_features:
            return templates.TemplateResponse(
                "home.html",
                _template_context(
                    request,
                    page_title=settings.app_name,
                    extra={
                        "message": "Unable to generate report without transaction history.",
                        "report_enabled": report_generation_enabled(),
                    },
                ),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Generate the markdown report
        report_markdown = await report_service.generate_markdown_report(result)

        # Get grade info
        grade_info = get_grade_info(result.credit_score)

        # Combine all features
        all_features = {
            **result.onchain_features,
            **result.offchain_data,
        }

        context = {
            "wallet_address": result.wallet_address,
            "credit_score": result.credit_score,
            "transaction_count": result.transaction_count,
            "grade_info": grade_info,
            "features": all_features,
            "onchain_features": result.onchain_features,
            "offchain_data": result.offchain_data,
            "report_markdown": report_markdown,
            "report_markdown_raw": report_markdown,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        return templates.TemplateResponse(
            "report.html",
            _template_context(
                request,
                page_title=f"Credit Report - {result.wallet_address}",
                extra=context,
            ),
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error generating report: {e}", exc_info=True)

        return templates.TemplateResponse(
            "home.html",
            _template_context(
                request,
                page_title=settings.app_name,
                extra={
                    "message": f"Error generating report: {str(e)}",
                    "report_enabled": report_generation_enabled(),
                },
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
