"""
RateLimiter - Simple rate limiting for API requests.
"""
import asyncio


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, interval: float):
        """
        Initialize rate limiter.
        
        Args:
            interval: Minimum seconds between requests
        """
        self.interval = interval
        self.lock = asyncio.Lock()
        self.last_called = 0
    
    async def __aenter__(self):
        """Wait if necessary before allowing request."""
        async with self.lock:
            now = asyncio.get_event_loop().time()
            wait_time = self.interval - (now - self.last_called)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_called = asyncio.get_event_loop().time()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        pass