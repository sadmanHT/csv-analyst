"""
Custom Exception Classes for CSV Analyst Backend
"""

class ExecutionTimeoutError(RuntimeError):
    """Raised when sandboxed code execution exceeds the configured time limit."""

class SecurityError(ValueError):
    """Raised when code AST or parameter validation detects forbidden operations."""

class DataValidationError(ValueError):
    """Raised when input data violates schema or shape constraints."""

class LLMSynthesisError(RuntimeError):
    """Raised when LLM synthesis fails fatally."""

class ExecutionBudgetExceededError(RuntimeError):
    """Raised when request LLM call quota or timeout budget is exceeded."""
