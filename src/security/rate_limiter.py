"""
Rate Limiting System

Provides multi-layer rate limiting with token bucket algorithm, circuit breakers,
and DDoS protection for the MCP documentation server.
"""

import asyncio
import json
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel


class RateLimitType(Enum):
    """Types of rate limiting"""
    REQUESTS_PER_SECOND = "rps"
    REQUESTS_PER_MINUTE = "rpm"
    REQUESTS_PER_HOUR = "rph"
    REQUESTS_PER_DAY = "rpd"
    API_CALLS_PER_HOUR = "api_cph"  # For external API calls
    COST_BASED = "cost"             # For expensive operations


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    limit: int                      # Maximum requests
    window_seconds: int             # Time window
    burst_limit: int = None         # Burst allowance
    cost_per_request: float = 1.0   # Cost weight
    reset_on_success: bool = False  # Reset counter on successful requests


class RateLimitResult(BaseModel):
    """Rate limiting result"""
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    cost_used: float = 0.0
    reason: Optional[str] = None


class TokenBucket:
    """Token bucket algorithm implementation"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket"""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait until tokens are available"""
        if self.tokens >= tokens:
            return 0.0
        
        needed_tokens = tokens - self.tokens
        return needed_tokens / self.refill_rate


class CircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception(f"Circuit breaker OPEN. Try again in {self.timeout - (time.time() - self.last_failure_time):.1f}s")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
            self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            
            raise e


class RateLimiter:
    """Multi-layer rate limiter with token bucket and sliding window"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, TokenBucket] = {}
        self.local_windows: Dict[str, deque] = defaultdict(deque)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Default rules
        self.default_rules = {
            RateLimitType.REQUESTS_PER_SECOND: RateLimitRule(10, 1, burst_limit=20),
            RateLimitType.REQUESTS_PER_MINUTE: RateLimitRule(100, 60, burst_limit=150),
            RateLimitType.REQUESTS_PER_HOUR: RateLimitRule(1000, 3600, burst_limit=1200),
            RateLimitType.API_CALLS_PER_HOUR: RateLimitRule(100, 3600, cost_per_request=1.0),
        }
    
    async def is_allowed(
        self,
        identifier: str,
        limit_type: RateLimitType,
        rule: Optional[RateLimitRule] = None,
        cost: float = 1.0
    ) -> RateLimitResult:
        """Check if request is allowed under rate limits"""
        
        rule = rule or self.default_rules.get(limit_type)
        if not rule:
            return RateLimitResult(allowed=True, limit=999999, remaining=999999, reset_time=0)
        
        key = f"{identifier}:{limit_type.value}"
        now = time.time()
        
        # Use Redis for distributed rate limiting if available
        if self.redis_client:
            return await self._redis_rate_limit(key, rule, cost, now)
        else:
            return await self._local_rate_limit(key, rule, cost, now)
    
    async def _redis_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
        cost: float,
        now: float
    ) -> RateLimitResult:
        """Redis-based distributed rate limiting"""
        
        # Use Redis sliding window counter
        pipe = self.redis_client.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, now - rule.window_seconds)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        request_id = f"{now}:{id(asyncio.current_task())}"
        pipe.zadd(key, {request_id: now})
        
        # Set expiry
        pipe.expire(key, rule.window_seconds)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Calculate cost-adjusted count
        cost_adjusted_count = current_count * rule.cost_per_request
        
        if cost_adjusted_count + cost <= rule.limit:
            # Request allowed
            remaining = int(rule.limit - cost_adjusted_count - cost)
            reset_time = int(now + rule.window_seconds)
            
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=remaining,
                reset_time=reset_time,
                cost_used=cost
            )
        else:
            # Request denied - remove the request we added
            await self.redis_client.zrem(key, request_id)
            
            # Calculate retry after
            oldest_score = await self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_score:
                retry_after = int(oldest_score[0][1] + rule.window_seconds - now)
            else:
                retry_after = rule.window_seconds
            
            return RateLimitResult(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=int(now + rule.window_seconds),
                retry_after=max(1, retry_after),
                cost_used=0,
                reason="Rate limit exceeded"
            )
    
    async def _local_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
        cost: float,
        now: float
    ) -> RateLimitResult:
        """Local in-memory rate limiting"""
        
        # Use token bucket for burst handling
        if rule.burst_limit:
            bucket_key = f"{key}:bucket"
            if bucket_key not in self.local_buckets:
                refill_rate = rule.limit / rule.window_seconds
                self.local_buckets[bucket_key] = TokenBucket(rule.burst_limit, refill_rate)
            
            bucket = self.local_buckets[bucket_key]
            tokens_needed = int(cost)
            
            if bucket.consume(tokens_needed):
                return RateLimitResult(
                    allowed=True,
                    limit=rule.limit,
                    remaining=int(bucket.tokens),
                    reset_time=int(now + rule.window_seconds),
                    cost_used=cost
                )
            else:
                wait_time = bucket.get_wait_time(tokens_needed)
                return RateLimitResult(
                    allowed=False,
                    limit=rule.limit,
                    remaining=0,
                    reset_time=int(now + rule.window_seconds),
                    retry_after=int(wait_time) + 1,
                    cost_used=0,
                    reason="Token bucket depleted"
                )
        
        # Use sliding window
        window = self.local_windows[key]
        
        # Remove expired entries
        while window and window[0] <= now - rule.window_seconds:
            window.popleft()
        
        # Check limit
        current_count = len(window)
        if current_count + cost <= rule.limit:
            # Request allowed
            window.append(now)
            remaining = int(rule.limit - current_count - cost)
            
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=remaining,
                reset_time=int(now + rule.window_seconds),
                cost_used=cost
            )
        else:
            # Request denied
            oldest_time = window[0] if window else now
            retry_after = int(oldest_time + rule.window_seconds - now)
            
            return RateLimitResult(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_time=int(now + rule.window_seconds),
                retry_after=max(1, retry_after),
                cost_used=0,
                reason="Sliding window limit exceeded"
            )
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create circuit breaker for external service"""
        
        if service not in self.circuit_breakers:
            # Configure circuit breakers for different services
            config = {
                'github': {'failure_threshold': 3, 'timeout': 300},
                'pypi': {'failure_threshold': 5, 'timeout': 120},
                'npm': {'failure_threshold': 5, 'timeout': 120},
                'default': {'failure_threshold': 3, 'timeout': 60}
            }
            
            service_config = config.get(service, config['default'])
            self.circuit_breakers[service] = CircuitBreaker(**service_config)
        
        return self.circuit_breakers[service]
    
    async def api_call_with_protection(
        self,
        service: str,
        identifier: str,
        func,
        *args,
        **kwargs
    ):
        """Make API call with rate limiting and circuit breaker protection"""
        
        # Check rate limit first
        rate_limit_result = await self.is_allowed(
            identifier,
            RateLimitType.API_CALLS_PER_HOUR,
            cost=1.0
        )
        
        if not rate_limit_result.allowed:
            raise Exception(f"API rate limit exceeded. Retry after {rate_limit_result.retry_after}s")
        
        # Use circuit breaker
        circuit_breaker = self.get_circuit_breaker(service)
        
        try:
            result = await circuit_breaker.call(func, *args, **kwargs)
            return result
        except Exception as e:
            # Log the failure but don't expose internal details
            raise Exception(f"External API temporarily unavailable: {service}")


class CostBasedRateLimiter:
    """Cost-based rate limiter for expensive operations"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.cost_windows: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    
    async def consume_cost(
        self,
        identifier: str,
        cost: float,
        budget: float,
        window_seconds: int = 3600
    ) -> RateLimitResult:
        """Consume cost from user's budget"""
        
        key = f"cost:{identifier}"
        now = time.time()
        
        if self.redis_client:
            return await self._redis_cost_limit(key, cost, budget, window_seconds, now)
        else:
            return await self._local_cost_limit(key, cost, budget, window_seconds, now)
    
    async def _redis_cost_limit(
        self,
        key: str,
        cost: float,
        budget: float,
        window_seconds: int,
        now: float
    ) -> RateLimitResult:
        """Redis-based cost limiting"""
        
        # Use Redis sorted set to track costs with timestamps
        pipe = self.redis_client.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        
        # Calculate current cost usage
        pipe.zrange(key, 0, -1, withscores=True)
        
        results = await pipe.execute()
        cost_entries = results[1]
        
        current_cost = sum(score for _, score in cost_entries)
        
        if current_cost + cost <= budget:
            # Add the new cost
            await self.redis_client.zadd(key, {f"{now}:{cost}": cost})
            await self.redis_client.expire(key, window_seconds)
            
            return RateLimitResult(
                allowed=True,
                limit=int(budget),
                remaining=int(budget - current_cost - cost),
                reset_time=int(now + window_seconds),
                cost_used=cost
            )
        else:
            # Budget exceeded
            oldest_entry = cost_entries[0] if cost_entries else None
            if oldest_entry:
                oldest_time = float(oldest_entry[0].decode().split(':')[0])
                retry_after = int(oldest_time + window_seconds - now)
            else:
                retry_after = window_seconds
            
            return RateLimitResult(
                allowed=False,
                limit=int(budget),
                remaining=0,
                reset_time=int(now + window_seconds),
                retry_after=max(1, retry_after),
                cost_used=0,
                reason="Cost budget exceeded"
            )
    
    async def _local_cost_limit(
        self,
        key: str,
        cost: float,
        budget: float,
        window_seconds: int,
        now: float
    ) -> RateLimitResult:
        """Local cost limiting"""
        
        cost_window = self.cost_windows[key]
        
        # Remove expired entries
        while cost_window and cost_window[0][0] <= now - window_seconds:
            cost_window.pop(0)
        
        # Calculate current cost
        current_cost = sum(entry[1] for entry in cost_window)
        
        if current_cost + cost <= budget:
            # Add new cost
            cost_window.append((now, cost))
            
            return RateLimitResult(
                allowed=True,
                limit=int(budget),
                remaining=int(budget - current_cost - cost),
                reset_time=int(now + window_seconds),
                cost_used=cost
            )
        else:
            # Budget exceeded
            oldest_time = cost_window[0][0] if cost_window else now
            retry_after = int(oldest_time + window_seconds - now)
            
            return RateLimitResult(
                allowed=False,
                limit=int(budget),
                remaining=0,
                reset_time=int(now + window_seconds),
                retry_after=max(1, retry_after),
                cost_used=0,
                reason="Cost budget exceeded"
            )


class DDoSProtection:
    """DDoS protection with various detection methods"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.suspicious_ips: Dict[str, float] = {}
        self.blocked_ips: Dict[str, float] = {}
    
    async def is_suspicious(self, client_ip: str, request_path: str = None) -> bool:
        """Check if IP shows suspicious behavior"""
        
        now = time.time()
        
        # Clean up old entries
        self.suspicious_ips = {ip: timestamp for ip, timestamp in self.suspicious_ips.items() 
                               if now - timestamp < 3600}
        self.blocked_ips = {ip: timestamp for ip, timestamp in self.blocked_ips.items() 
                            if now - timestamp < 86400}
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return True
        
        # Simple heuristics for suspicious behavior
        if client_ip in self.suspicious_ips:
            # IP was flagged recently
            if now - self.suspicious_ips[client_ip] < 300:  # 5 minutes
                self.blocked_ips[client_ip] = now
                return True
        
        return False
    
    def mark_suspicious(self, client_ip: str, reason: str = "rate_limit_exceeded"):
        """Mark IP as suspicious"""
        self.suspicious_ips[client_ip] = time.time()
    
    def block_ip(self, client_ip: str, duration: int = 86400):
        """Block IP for specified duration (default 24h)"""
        self.blocked_ips[client_ip] = time.time()


# Rate limiting decorators and utilities
def rate_limit_key(user_id: str = None, client_ip: str = None, endpoint: str = None) -> str:
    """Generate rate limiting key"""
    if user_id:
        return f"user:{user_id}"
    elif client_ip:
        return f"ip:{client_ip}"
    elif endpoint:
        return f"endpoint:{endpoint}"
    else:
        return "global"


async def check_multiple_limits(
    rate_limiter: RateLimiter,
    identifier: str,
    limits: List[Tuple[RateLimitType, RateLimitRule]]
) -> RateLimitResult:
    """Check multiple rate limits and return the most restrictive result"""
    
    for limit_type, rule in limits:
        result = await rate_limiter.is_allowed(identifier, limit_type, rule)
        if not result.allowed:
            return result
    
    # All limits passed
    return RateLimitResult(allowed=True, limit=999999, remaining=999999, reset_time=0)