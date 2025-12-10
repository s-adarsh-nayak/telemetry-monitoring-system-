import random
import time
import logging
import json
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import uvicorn

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","module":"%(module)s"}'
)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
resource = Resource.create({"service.name": "sample-api"})

# Tracing
trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Prometheus metrics
prom_requests = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
prom_latency = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

app = FastAPI(title="Sample Observability API")
FastAPIInstrumentor.instrument_app(app)

# Sample data
USERS_DB = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
]

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"status": "ok", "service": "sample-api"}

@app.get("/api/users")
async def get_users():
    with tracer.start_as_current_span("get_users") as span:
        start = time.time()
        
        # Simulate processing
        time.sleep(random.uniform(0.05, 0.3))
        
        # Randomly inject errors (5% chance)
        if random.random() < 0.05:
            logger.error("Failed to fetch users", extra={"error_code": "DB_ERROR"})
            prom_requests.labels(method="GET", endpoint="/api/users", status="500").inc()
            span.set_attribute("error", True)
            raise HTTPException(status_code=500, detail="Database error")
        
        logger.info(f"Fetched {len(USERS_DB)} users", extra={"count": len(USERS_DB)})
        prom_requests.labels(method="GET", endpoint="/api/users", status="200").inc()
        prom_latency.labels(method="GET", endpoint="/api/users").observe(time.time() - start)
        
        span.set_attribute("user.count", len(USERS_DB))
        return {"users": USERS_DB}

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    with tracer.start_as_current_span("get_user") as span:
        start = time.time()
        span.set_attribute("user.id", user_id)
        
        time.sleep(random.uniform(0.02, 0.15))
        
        user = next((u for u in USERS_DB if u["id"] == user_id), None)
        
        if not user:
            logger.warning(f"User not found: {user_id}", extra={"user_id": user_id})
            prom_requests.labels(method="GET", endpoint="/api/users/{id}", status="404").inc()
            span.set_attribute("error", True)
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Fetched user: {user_id}", extra={"user_id": user_id})
        prom_requests.labels(method="GET", endpoint="/api/users/{id}", status="200").inc()
        prom_latency.labels(method="GET", endpoint="/api/users/{id}").observe(time.time() - start)
        
        return user

@app.get("/api/slow")
async def slow_endpoint():
    """Endpoint that simulates slow response"""
    with tracer.start_as_current_span("slow_endpoint"):
        logger.warning("Slow endpoint called")
        time.sleep(random.uniform(0.5, 1.5))  # Deliberately slow
        prom_requests.labels(method="GET", endpoint="/api/slow", status="200").inc()
        return {"message": "This was slow"}

@app.get("/api/error")
async def error_endpoint():
    """Endpoint that always errors"""
    logger.error("Intentional error triggered", extra={"error_type": "intentional"})
    prom_requests.labels(method="GET", endpoint="/api/error", status="500").inc()
    raise HTTPException(status_code=500, detail="Intentional error for testing")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/logs")
async def generate_logs():
    """Generate sample logs for testing"""
    logger.debug("Debug log message")
    logger.info("Info log message", extra={"user": "test", "action": "view"})
    logger.warning("Warning log message", extra={"threshold": 80, "current": 85})
    logger.error("Error log message", extra={"error_code": "ERR_001"})
    return {"message": "Logs generated"}

if __name__ == "__main__":
    logger.info("Starting Sample API")
    uvicorn.run(app, host="0.0.0.0", port=8000)
