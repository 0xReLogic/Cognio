"""Request logging and metrics tracking."""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for tracking API metrics."""

    def __init__(self) -> None:
        """Initialize metrics tracking."""
        self.request_count = 0
        self.total_response_time = 0.0
        self.endpoint_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_time": 0.0, "errors": 0}
        )
        self.start_time = datetime.now()

    def record_request(self, endpoint: str, response_time: float, error: bool = False) -> None:
        """
        Record a request metric.

        Args:
            endpoint: The API endpoint
            response_time: Time taken in seconds
            error: Whether the request resulted in an error
        """
        self.request_count += 1
        self.total_response_time += response_time

        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += response_time
        if error:
            stats["errors"] += 1

        logger.info(
            f"Request to {endpoint} completed in {response_time:.3f}s "
            f"(error: {error})"
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get current metrics statistics.

        Returns:
            Dictionary with metrics data
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        avg_response_time = (
            self.total_response_time / self.request_count if self.request_count > 0 else 0
        )

        endpoint_details = {}
        for endpoint, stats in self.endpoint_stats.items():
            endpoint_details[endpoint] = {
                "count": stats["count"],
                "avg_time": stats["total_time"] / stats["count"] if stats["count"] > 0 else 0,
                "errors": stats["errors"],
            }

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "avg_response_time": avg_response_time,
            "endpoints": endpoint_details,
        }


# Global metrics instance
metrics_service = MetricsService()
