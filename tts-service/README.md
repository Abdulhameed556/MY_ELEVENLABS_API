"""
README for TTS Microservice
"""

# TTS Microservice 🎙️

Production-ready Text-to-Speech microservice using ElevenLabs API, built with FastAPI and MLOps best practices.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone/navigate to the project
cd tts-service

# Copy environment template
cp .env.example .env

# Edit .env and add your ElevenLabs API key
# TTS_ELEVENLABS_API_KEY=your_actual_api_key_here
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or use make for convenience
make install
```

### 3. Run the Service

```bash
# Development mode (auto-reload)
make dev

# Production mode (single worker)
make run

# Production mode (multi-worker, Windows example)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# Or with Docker
make docker-run
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/v1/tts/health

# List available voices
curl http://localhost:8000/v1/tts/voices

# Generate TTS (example)
curl -X POST http://localhost:8000/v1/tts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "news_id": "news_123",
    "title": "Breaking News",
    "body": "This is a sample news article for TTS generation.",
    "voice": "sarah",
    "format": "mp3"
  }' \
  --output audio.mp3
```

Windows one‑liners:

- PowerShell

```powershell
curl -sS -X POST "http://127.0.0.1:8000/v1/tts/generate" -H "Content-Type: application/json" -d '{"news_id":"news_123","title":"Breaking News","body":"Sample text.","voice":"adam","format":"mp3"}' --output .\audio\out.mp3 -w " HTTP_STATUS=%{http_code}`n" ; start .\audio\out.mp3
```

- cmd.exe

```bat
curl -sS -X POST "http://127.0.0.1:8000/v1/tts/generate" -H "Content-Type: application/json" -d "{\"news_id\":\"news_123\",\"title\":\"Breaking News\",\"body\":\"Sample text.\",\"voice\":\"adam\",\"format\":\"mp3\"}" --output audio\out.mp3 -w " HTTP_STATUS=%{http_code}\n" & start "" audio\out.mp3
```

## 📁 Project Structure

```
tts-service/
├── app/
│   ├── api/                   # API routes
│   │   └── routes_tts.py      # TTS endpoints
│   ├── core/                  # Configuration & logging
│   │   ├── config.py          # Settings management
│   │   └── logger.py          # Structured logging
│   ├── middleware/            # Cross-cutting concerns
│   │   ├── request_logger.py  # Request logging
│   │   ├── error_handler.py   # Exception handling
│   │   └── metrics.py         # Prometheus metrics
│   ├── models/                # Pydantic models
│   │   ├── request_models.py  # Request schemas
│   │   └── response_models.py # Response schemas
│   ├── services/              # Business logic
│   │   ├── elevenlabs_service.py # ElevenLabs integration
│   │   └── voice_manager.py   # Voice configuration
│   ├── utils/                 # Utilities
│   │   ├── chunking.py        # Text processing
│   │   └── audio_utils.py     # Audio processing
│   └── main.py               # FastAPI application
├── tests/                    # Test suite
├── config.yaml              # Voice configuration
├── requirements.txt         # Dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Multi-service setup
└── Makefile               # Development commands
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
TTS_ELEVENLABS_API_KEY=sk_your_key_here

# Optional (with defaults)
TTS_DEBUG=False
TTS_API_HOST=0.0.0.0
TTS_API_PORT=8000
TTS_MAX_TEXT_LENGTH=10000
TTS_LOG_LEVEL=INFO
```

Notes:
- Environment variables are prefixed with `TTS_` and loaded via `pydantic-settings`.
- Place `.env` in `tts-service/` (service root). `.env` is git‑ignored.
- Rotate your API key immediately if it was ever exposed; never commit secrets.

### Voice Configuration (config.yaml)

Add/modify voices in `config.yaml`:

```yaml
voices:
  sarah:
    voice_id: "EXAVITQu4vr4xnSDxMaL"
    model: "eleven_turbo_v2_5"
    description: "Professional Female"
    category: "news"
    settings:
      stability: 0.7
      similarity_boost: 0.6
```

## 🔄 Workflow

1. **Admin publishes article** → Node.js backend intercepts
2. **Node.js calls your TTS API** → `POST /v1/tts/generate`
3. **TTS service generates audio** → Returns MP3 bytes
4. **Node.js caches audio** → Stores in S3/database
5. **Users request audio** → Served from Node.js cache

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service information |
| `/v1/tts/generate` | POST | Generate TTS audio |
| `/v1/tts/voices` | GET | List available voices |
| `/v1/tts/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### Generate TTS Request

```json
{
  "news_id": "article_123",
  "title": "Article Title",
  "body": "Article content...",
  "voice": "sarah",
  "format": "mp3",
  "sample_rate": 22050,
  "metadata": {
    "author": "John Doe",
    "category": "technology"
  }
}
```

### Generate TTS Response

Returns audio stream with headers:
- `X-Request-ID`: Unique request identifier
- `X-News-ID`: Article identifier
- `X-Voice-Used`: Voice used for generation
- `X-Audio-Size`: Audio file size in bytes

Additionally, the `X-Metadata` header contains a JSON string with enriched information, for example:

```json
{
  "request_id": "<uuid>",
  "news_id": "article_123",
  "status": "success",
  "audio_size_bytes": 123342,
  "duration_seconds": null,
  "format": "mp3",
  "sample_rate": 22050,
  "voice_used": "adam",
  "model_used": "eleven_flash_v2_5",
  "chars_processed": 111,
  "generation_time_ms": 2535,
  "created_at": "2025-09-21T07:05:21.906138Z",
  "metadata": {
    "audio_info": {
      "duration_seconds": null,
      "frame_rate": null,
      "channels": null,
      "sample_width": null,
      "size_bytes": 123342,
      "format": "mp3"
    },
    "voice_config": "Authoritative Male"
  }
}
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Integration tests only
pytest tests/test_api.py
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
mypy app/
```

### Local Development with Monitoring

```bash
# Start with Prometheus + Grafana
docker-compose up --build

# Access services:
# - TTS API: http://localhost:8000
# - Prometheus: http://localhost:9091  
# - Grafana: http://localhost:3000 (admin/admin)
```

## 📈 Monitoring & Observability

### Metrics (Prometheus)

- `tts_requests_total` - Request counter by voice/status
- `tts_request_duration_seconds` - Request latency
- `tts_generation_duration_seconds` - TTS generation time
- `tts_characters_processed_total` - Characters processed
- `tts_errors_total` - Error counter by type

### Logging (Structured JSON)

```json
{
  "timestamp": "2025-09-20T10:30:45Z",
  "level": "INFO",
  "request_id": "abc-123",
  "news_id": "n567",
  "voice": "sarah", 
  "chars_count": 1024,
  "duration_ms": 1340,
  "message": "TTS generation completed"
}
```

### Health Monitoring

```bash
# Health check
curl http://localhost:8000/v1/tts/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

## 🚀 Deployment

### Docker

```bash
# Build image
make build

# Run container
docker run -p 8000:8000 \
  -e TTS_ELEVENLABS_API_KEY=your_key \
  tts-service:latest
```

### Kubernetes (with Helm - optional)

```bash
# Install with Helm
helm install tts-service ./helm/

# Or apply Kubernetes manifests
kubectl apply -f k8s/
```

## 🔒 Production Considerations

### Security

- Store API keys in a secrets manager (avoid hardcoding in images)
- Configure proper CORS origins
- Use HTTPS with valid certificates
- Implement rate limiting per client
- Run as non-root user in containers
 - Rotate keys immediately if exposed; validate via a quick health/generate test after rotation

### Performance

- Monitor ElevenLabs API quotas and costs
- Implement circuit breakers for upstream failures
- Use connection pooling for HTTP requests
- Consider async processing for very long articles
 - Scale Uvicorn workers: start with `--workers <cpu_cores>` and tune
 - Consider Linux with Gunicorn+Uvicorn workers for higher throughput

### Reliability

- Set up health checks and auto-restart
- Configure proper resource limits
- Implement backup ElevenLabs accounts
- Monitor disk space for temporary files

### Concurrency & Rate Limiting

- The service is fully async (FastAPI + `httpx.AsyncClient`) and supports many concurrent in‑flight requests.
- ElevenLabs enforces upstream rate limits; bursts may receive HTTP 429. Retries with backoff/jitter are implemented and `Retry-After` is honored.
- For very high concurrency, add a small semaphore around upstream calls or a per‑client rate limiter.

## 🐛 Troubleshooting

### Common Issues

1. **"API key is required" error**
   - Check `.env` file has correct `TTS_ELEVENLABS_API_KEY`
   - Ensure API key is valid and has credits

2. **"Voice not found" error**
   - Check voice name in `config.yaml`
   - Verify voice ID is correct for your ElevenLabs account

3. **Audio generation fails**
   - Check ElevenLabs quota/credits
   - Verify internet connectivity
   - Check logs for detailed error messages
  - If you receive a plain `Internal Server Error`, ensure the service isn’t restarting. Errors normally return structured JSON with `x-request-id`.

4. **High memory usage**
   - Large audio files are processed in memory
   - Consider reducing `chunk_size` for very long texts

5. **Windows quoting problems**
   - Prefer a PowerShell here‑string for long JSON bodies:

```powershell
$body = @'
{ "news_id": "n1", "title": "t", "body": "b", "voice": "adam", "format": "mp3" }
'@
curl -sS -X POST "http://127.0.0.1:8000/v1/tts/generate" -H "Content-Type: application/json" -d $body --output .\audio\out.mp3
```

### Structured Error Responses

The global error handler returns JSON with a timestamp and error code; `x-request-id` helps correlate logs.

```json
{
  "error": {
    "code": "UPSTREAM_ERROR",
    "message": "ElevenLabs returned 429",
    "details": { "retry_after": 2 }
  },
  "timestamp": "2025-09-21T06:44:09Z",
  "request_id": "fc8fa8bb-1df2-4039-9c7d-f84dcc6da2c7"
}
```

### Optional audio metadata enrichment

Install system `ffmpeg` so `duration_seconds` and `frame_rate` in `X-Metadata` can populate (in addition to `pydub`):

```bash
# Windows (one-time)
winget install -e --id Gyan.FFmpeg
```

---

## 🤝 Node.js Integration (handoff guide)

Your Node backend can call `POST /v1/tts/generate` and stream the audio to clients. Two minimal patterns are below.

### A) Minimal Node 18+ script (fetch)

```js
// tts_client.mjs
import { writeFile } from 'node:fs/promises';

const payload = {
  news_id: 'news_123',
  title: 'Breaking News',
  body: 'Sample text.',
  voice: 'adam',
  format: 'mp3'
};

const res = await fetch('http://127.0.0.1:8000/v1/tts/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

if (!res.ok) {
  let errJson = null; try { errJson = await res.json(); } catch {}
  throw new Error(`TTS error ${res.status}: ${errJson ? JSON.stringify(errJson) : await res.text()}`);
}

const meta = res.headers.get('x-metadata');
const buf = Buffer.from(await res.arrayBuffer());
await writeFile('audio/out.mp3', buf);
console.log('Saved audio to audio/out.mp3');
console.log('Metadata:', meta ? JSON.parse(meta) : null);
```

### B) Express proxy that streams to browser

```js
// server.mjs
import express from 'express';
import { Readable } from 'node:stream';

const app = express();
app.use(express.json({ limit: '1mb' }));

app.post('/api/tts', async (req, res) => {
  try {
    const upstream = await fetch('http://127.0.0.1:8000/v1/tts/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req.body)
    });
    if (!upstream.ok) {
      let errJson = null; try { errJson = await upstream.json(); } catch {}
      return res.status(upstream.status).json(errJson ?? { message: 'TTS upstream error' });
    }
    const ct = upstream.headers.get('content-type') || 'audio/mpeg';
    res.setHeader('Content-Type', ct);
    const xMeta = upstream.headers.get('x-metadata'); if (xMeta) res.setHeader('x-metadata', xMeta);
    const xReq = upstream.headers.get('x-request-id'); if (xReq) res.setHeader('x-request-id', xReq);
    Readable.fromWeb(upstream.body).pipe(res);
  } catch (err) {
    res.status(502).json({ message: 'TTS proxy error', detail: String(err) });
  }
});

app.listen(3000, () => console.log('Node proxy on http://127.0.0.1:3000'));
```

Contract summary for Node team:
- Endpoint: `POST /v1/tts/generate`
- Body: `{ news_id: string, title: string, body: string, voice: 'adam'|'sarah'|'arnold', format: 'mp3', sample_rate?: number }`
- Success: `200 OK` with `audio/mp3` body, headers `x-request-id`, `x-metadata`, `x-voice-used`, `x-audio-size`
- Errors: JSON body with `error.code`, `error.message`, and `x-request-id`

---

## ✅ Production‑readiness checklist

- [ ] `.env` configured with `TTS_ELEVENLABS_API_KEY` (and rotated if previously exposed)
- [ ] Health/voices/generate endpoints return 200 locally
- [ ] Optional: `ffmpeg` installed for enriched metadata
- [ ] Observability: `/metrics` scraped or reachable; logs collected
- [ ] Concurrency sized (Uvicorn `--workers` tuned for CPU)
- [ ] Error responses confirmed structured (carry `x-request-id`)

### Getting Help

- Check logs: `docker-compose logs tts-service`
- Health endpoint: `GET /v1/tts/health`
- Metrics: `GET /metrics`

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ using FastAPI, ElevenLabs, and MLOps best practices**