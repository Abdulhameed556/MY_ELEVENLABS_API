"""
Prometheus Metrics Middleware and Collectors
"""

import time
from typing import Dict
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# --------------------------
# Metrics Definitions
# --------------------------

tts_requests_total = Counter(
    "tts_requests_total",
    "Total TTS requests",
    ["method", "route", "status_code", "voice"]
)

tts_request_duration_seconds = Histogram(
    "tts_request_duration_seconds",
    "Time spent processing TTS requests",
    ["method", "route", "voice"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

tts_generation_duration_seconds = Histogram(
    "tts_generation_duration_seconds",
    "Time spent generating TTS audio",
    ["voice", "model"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

tts_characters_processed_total = Counter(
    "tts_characters_processed_total",
    "Total characters processed by TTS",
    ["voice", "model"]
)

tts_audio_size_bytes = Histogram(
    "tts_audio_size_bytes",
    "Size of generated audio files",
    ["voice", "format"],
    buckets=[10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
)

tts_errors_total = Counter(
    "tts_errors_total",
    "Total TTS errors",
    ["error_code", "voice", "retryable"]
)

elevenlabs_api_requests_total = Counter(
    "elevenlabs_api_requests_total",
    "Total requests to ElevenLabs API",
    ["status_code", "voice_id"]
)

elevenlabs_api_duration_seconds = Histogram(
    "elevenlabs_api_duration_seconds",
    "Time spent calling ElevenLabs API",
    ["voice_id"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

tts_active_requests = Gauge(
    "tts_active_requests",
    "Number of active TTS requests"
)

# --------------------------
# Middleware
# --------------------------

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics"""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics collection for metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        tts_active_requests.inc()
        method = request.method
        # Prefer a stable string label for the route to avoid non-serializable objects
        route_label = request.url.path
        voice = getattr(request.state, "voice_used", "unknown")

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Record metrics defensively; never let metrics failures break requests
            try:
                tts_requests_total.labels(
                    method=str(method),
                    route=str(route_label),
                    status_code=str(response.status_code),
                    voice=str(voice),
                ).inc()

                tts_request_duration_seconds.labels(
                    method=str(method),
                    route=str(route_label),
                    voice=str(voice),
                ).observe(duration)
            except Exception:
                # Swallow metrics errors to avoid impacting user responses
                pass

            return response

        except Exception:
            # Record as internal error
            tts_errors_total.labels(
                error_code="INTERNAL_ERROR",
                voice=voice,
                retryable="false"
            ).inc()
            raise

        finally:
            tts_active_requests.dec()


# --------------------------
# Helper Class
# --------------------------

class TTSMetrics:
    """Helper class for recording TTS-specific metrics"""

    @staticmethod
    def record_generation(voice: str, model: str, duration: float, chars: int, audio_size: int, format: str):
        tts_generation_duration_seconds.labels(voice=voice, model=model).observe(duration)
        tts_characters_processed_total.labels(voice=voice, model=model).inc(chars)
        tts_audio_size_bytes.labels(voice=voice, format=format).observe(audio_size)

    @staticmethod
    def record_error(error_code: str, voice: str = "unknown", retryable: bool = True):
        tts_errors_total.labels(
            error_code=error_code,
            voice=voice,
            retryable=str(retryable).lower()
        ).inc()

    @staticmethod
    def record_elevenlabs_request(voice_id: str, duration: float, status_code: int):
        elevenlabs_api_requests_total.labels(
            status_code=str(status_code),
            voice_id=voice_id
        ).inc()
        elevenlabs_api_duration_seconds.labels(voice_id=voice_id).observe(duration)


# --------------------------
# Endpoint
# --------------------------

def create_metrics_endpoint():
    async def metrics_endpoint(request: Request):
        metrics_output = generate_latest()
        return PlainTextResponse(content=metrics_output, headers={"Content-Type": CONTENT_TYPE_LATEST})
    return metrics_endpoint


metrics = TTSMetrics()