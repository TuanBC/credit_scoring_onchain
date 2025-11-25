"""High-level orchestration of the credit scoring workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from fastapi import HTTPException

from services.credit_scoring_service import CreditScoringService
from services.etherscan_service import EtherscanService
from services.offchain_data_generator import OffchainDataGenerator

from app.services.cache import InMemoryTTLCache


def _normalize_wallet_address(address: str) -> str:
    if not address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    address = address.strip()
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(
            status_code=400,
            detail="Wallet address must be a 42-char hex string starting with 0x",
        )
    return address.lower()


def _to_native(obj: Any) -> Any:
    """Recursively convert numpy/pandas objects to native Python types."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(v) for v in obj]
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


@dataclass(slots=True)
class ScoreComputation:
    wallet_address: str
    credit_score: float
    onchain_features: Dict[str, Any]
    offchain_data: Dict[str, Any]
    transaction_count: int
    time_series_data: Optional[Dict[str, Any]] = None
    card_info: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    def as_payload(self) -> Dict[str, Any]:
        return {
            "wallet_address": self.wallet_address,
            "breakdown": {
                "credit_score": self.credit_score,
                "features": self.onchain_features,
                "offchain_data": self.offchain_data,
                "card_info": self.card_info or {},
                "transaction_count": self.transaction_count,
                "time_series": self.time_series_data or {},
            },
            "message": self.message,
        }


class ScoringEngine:
    """Coordinates data fetching and scoring."""

    def __init__(
        self,
        etherscan_service: EtherscanService,
        credit_scoring_service: CreditScoringService,
        offchain_generator: OffchainDataGenerator,
        cache: Optional[InMemoryTTLCache["ScoreComputation"]] = None,
    ) -> None:
        self.etherscan_service = etherscan_service
        self.credit_scoring_service = credit_scoring_service
        self.offchain_generator = offchain_generator
        self.cache = cache

    async def evaluate_wallet(self, wallet_address: str) -> ScoreComputation:
        """Fetch transactions, compute features, and calculate score."""
        normalized_address = _normalize_wallet_address(wallet_address)

        if self.cache:
            cached = self.cache.get(normalized_address)
            if cached:
                return cached

        transactions = await self.etherscan_service.fetch_transactions(
            normalized_address
        )
        if not transactions:
            result = ScoreComputation(
                wallet_address=normalized_address,
                credit_score=0.0,
                onchain_features={},
                offchain_data={},
                transaction_count=0,
                message="No transaction history found for this wallet",
            )
            if self.cache:
                self.cache.set(normalized_address, result)
            return result

        features = self.credit_scoring_service.extract_features(
            transactions, normalized_address
        )
        features = _to_native(features)
        credit_score = float(
            self.credit_scoring_service.calculate_scorecard_credit_score(features)
        )

        # Extract time-series data for charts
        time_series_data = self.credit_scoring_service.extract_time_series_data(
            transactions, normalized_address
        )
        time_series_data = _to_native(time_series_data)

        offchain_data = self.offchain_generator.generate(normalized_address, features)

        result = ScoreComputation(
            wallet_address=normalized_address,
            credit_score=credit_score,
            onchain_features=features,
            offchain_data=offchain_data,
            transaction_count=len(transactions),
            time_series_data=time_series_data,
        )
        if self.cache:
            self.cache.set(normalized_address, result)
        return result
