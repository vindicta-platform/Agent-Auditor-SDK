"""
Custom exceptions for Agent-Auditor-SDK.
"""

from datetime import datetime
from typing import Optional


class AgentAuditorError(Exception):
    """Base exception for all Agent-Auditor-SDK errors."""
    pass


class QuotaExhaustedError(AgentAuditorError):
    """
    Raised when API quota is exhausted.
    
    Includes reset_time for user display.
    """
    
    def __init__(
        self, 
        message: str = "API quota exhausted",
        reset_time: Optional[datetime] = None
    ) -> None:
        super().__init__(message)
        self.reset_time = reset_time
    
    def __str__(self) -> str:
        if self.reset_time:
            return f"Quota exhausted. Resets at {self.reset_time.isoformat()}"
        return "Quota exhausted"


class RateLimitError(AgentAuditorError):
    """Raised when rate limit (RPM/TPM) is exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after_seconds: int = 60
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TaskExecutionError(AgentAuditorError):
    """Raised when a task fails to execute."""
    
    def __init__(
        self, 
        message: str,
        task_id: Optional[str] = None,
        retryable: bool = True
    ) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.retryable = retryable


class APIKeyError(AgentAuditorError):
    """Base for API key related errors."""
    pass


class APIKeyNotFoundError(APIKeyError):
    """Raised when no API key is configured."""
    pass


class InvalidAPIKeyError(APIKeyError):
    """Raised when API key is invalid."""
    pass
