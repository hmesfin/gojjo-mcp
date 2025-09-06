"""
Health Check HTTP Server

Provides HTTP endpoints for Docker health checks and monitoring.
Runs alongside the MCP server in production environments.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any

import httpx
from aiohttp import web, web_request
import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class HealthStatus(BaseModel):
    """Health status response model"""
    status: str
    timestamp: float
    uptime: float
    services: Dict[str, Any]
    version: str = "1.0.0"

class HealthCheckServer:
    """HTTP server for health checks and monitoring"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.start_time = time.time()
        self.app = web.Application()
        self.redis_client = None
        
        # Setup routes
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/health/detailed', self.detailed_health_check)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/ready', self.readiness_check)
        self.app.router.add_get('/live', self.liveness_check)
        
        logger.info(f"Health check server initialized on port {port}")
    
    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def index(self, request: web_request.Request) -> web.Response:
        """Root endpoint with basic server info"""
        info = {
            "service": "Django Vue MCP Documentation Server",
            "version": "1.0.0",
            "status": "running",
            "uptime": f"{time.time() - self.start_time:.2f}s",
            "endpoints": [
                "/health - Basic health check",
                "/health/detailed - Detailed health status",
                "/metrics - Server metrics",
                "/ready - Readiness probe",
                "/live - Liveness probe"
            ]
        }
        return web.json_response(info)
    
    async def health_check(self, request: web_request.Request) -> web.Response:
        """Basic health check endpoint"""
        try:
            status = await self._get_health_status()
            status_code = 200 if status.status == "healthy" else 503
            return web.json_response(status.dict(), status=status_code)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }, status=503)
    
    async def detailed_health_check(self, request: web_request.Request) -> web.Response:
        """Detailed health check with service dependencies"""
        try:
            status = await self._get_detailed_health_status()
            status_code = 200 if status.status == "healthy" else 503
            return web.json_response(status.dict(), status=status_code)
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }, status=503)
    
    async def metrics(self, request: web_request.Request) -> web.Response:
        """Server metrics endpoint"""
        try:
            metrics = await self._get_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return web.json_response({
                "error": str(e),
                "timestamp": time.time()
            }, status=500)
    
    async def readiness_check(self, request: web_request.Request) -> web.Response:
        """Kubernetes readiness probe"""
        try:
            # Check if all required services are available
            redis_healthy = await self._check_redis_health()
            
            if redis_healthy:
                return web.json_response({
                    "status": "ready",
                    "timestamp": time.time()
                })
            else:
                return web.json_response({
                    "status": "not ready",
                    "reason": "Redis not available",
                    "timestamp": time.time()
                }, status=503)
        except Exception as e:
            return web.json_response({
                "status": "not ready",
                "error": str(e),
                "timestamp": time.time()
            }, status=503)
    
    async def liveness_check(self, request: web_request.Request) -> web.Response:
        """Kubernetes liveness probe"""
        try:
            # Simple check that the server is alive
            uptime = time.time() - self.start_time
            return web.json_response({
                "status": "alive",
                "uptime": uptime,
                "timestamp": time.time()
            })
        except Exception as e:
            return web.json_response({
                "status": "dead",
                "error": str(e),
                "timestamp": time.time()
            }, status=503)
    
    async def _get_health_status(self) -> HealthStatus:
        """Get basic health status"""
        redis_healthy = await self._check_redis_health()
        
        overall_status = "healthy" if redis_healthy else "degraded"
        
        return HealthStatus(
            status=overall_status,
            timestamp=time.time(),
            uptime=time.time() - self.start_time,
            services={
                "redis": "healthy" if redis_healthy else "unhealthy"
            }
        )
    
    async def _get_detailed_health_status(self) -> HealthStatus:
        """Get detailed health status with external service checks"""
        services = {}
        
        # Check Redis
        redis_healthy = await self._check_redis_health()
        services["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "response_time": await self._measure_redis_response_time()
        }
        
        # Check external APIs
        pypi_healthy = await self._check_external_api("https://pypi.org/pypi/requests/json")
        services["pypi_api"] = {
            "status": "healthy" if pypi_healthy else "unhealthy",
            "url": "https://pypi.org"
        }
        
        npm_healthy = await self._check_external_api("https://registry.npmjs.org/axios")
        services["npm_api"] = {
            "status": "healthy" if npm_healthy else "unhealthy",
            "url": "https://registry.npmjs.org"
        }
        
        # Overall status
        critical_services = [redis_healthy]
        all_healthy = all(critical_services)
        external_apis = [pypi_healthy, npm_healthy]
        
        if all_healthy:
            if all(external_apis):
                overall_status = "healthy"
            else:
                overall_status = "degraded"  # External APIs down but core services up
        else:
            overall_status = "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            timestamp=time.time(),
            uptime=time.time() - self.start_time,
            services=services
        )
    
    async def _get_metrics(self) -> Dict[str, Any]:
        """Get server metrics"""
        import psutil
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        uptime = time.time() - self.start_time
        
        metrics = {
            "timestamp": time.time(),
            "uptime": uptime,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total
            },
            "application": {
                "version": "1.0.0",
                "start_time": self.start_time,
                "uptime_seconds": uptime
            }
        }
        
        # Add Redis metrics if available
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                metrics["redis"] = {
                    "version": redis_info.get("redis_version"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "used_memory": redis_info.get("used_memory"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses")
                }
            except Exception as e:
                metrics["redis"] = {"error": str(e)}
        
        return metrics
    
    async def _check_redis_health(self) -> bool:
        """Check Redis health"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    async def _measure_redis_response_time(self) -> float:
        """Measure Redis response time in milliseconds"""
        if not self.redis_client:
            return -1
        
        try:
            start_time = time.time()
            await self.redis_client.ping()
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception:
            return -1
    
    async def _check_external_api(self, url: str, timeout: float = 5.0) -> bool:
        """Check external API health"""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"External API health check failed for {url}: {e}")
            return False
    
    async def start_server(self):
        """Start the health check server"""
        try:
            # Initialize Redis connection
            await self.init_redis()
            
            # Start the web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"Health check server started on port {self.port}")
            
            # Keep the server running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
                
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Health check server cleanup completed")

async def main():
    """Main function for standalone health server"""
    port = int(os.getenv('HEALTH_PORT', '8080'))
    server = HealthCheckServer(port=port)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Health check server interrupted")
    finally:
        await server.cleanup()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())