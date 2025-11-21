"""
Lightweight profiling utility for measuring time spent in different operations.
Used to track performance of embedding, database, and Gemini API calls.
"""
import time
import logging
from typing import Dict, Optional
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class Profiler:
    """Lightweight profiler for tracking operation timings"""
    
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
    
    def start(self, operation: str) -> None:
        """Start timing an operation"""
        self.start_times[operation] = time.perf_counter()
    
    def end(self, operation: str) -> float:
        """End timing an operation and return elapsed time in seconds"""
        if operation not in self.start_times:
            logger.warning(f"Operation '{operation}' was not started")
            return 0.0
        
        elapsed = time.perf_counter() - self.start_times[operation]
        self.timings[operation] = elapsed
        del self.start_times[operation]
        return elapsed
    
    @contextmanager
    def measure(self, operation: str):
        """Context manager for measuring operation time"""
        self.start(operation)
        try:
            yield
        finally:
            self.end(operation)
    
    def get_timings(self) -> Dict[str, float]:
        """Get all recorded timings"""
        return self.timings.copy()
    
    def get_total(self) -> float:
        """Get total time across all measured operations"""
        return sum(self.timings.values())
    
    def log_summary(self, prefix: str = "") -> None:
        """Log a summary of all timings"""
        if not self.timings:
            return
        
        total = self.get_total()
        lines = [f"{prefix}Profiling Summary:"]
        
        # Sort by time (descending)
        sorted_timings = sorted(self.timings.items(), key=lambda x: x[1], reverse=True)
        
        for operation, elapsed in sorted_timings:
            percentage = (elapsed / total * 100) if total > 0 else 0
            lines.append(f"{prefix}  {operation}: {elapsed*1000:.2f}ms ({percentage:.1f}%)")
        
        lines.append(f"{prefix}  Total: {total*1000:.2f}ms")
        logger.info("\n".join(lines))
    
    def reset(self) -> None:
        """Reset all timings"""
        self.timings.clear()
        self.start_times.clear()


# Global profiler instance (can be overridden per request)
_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """Get or create the current profiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = Profiler()
    return _profiler


def reset_profiler() -> Profiler:
    """Reset the global profiler and return the new instance"""
    global _profiler
    _profiler = Profiler()
    return _profiler


def profile_function(operation_name: str):
    """Decorator to profile a function"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.measure(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

