# Local REST API

## Overview

The Local REST API is a **fully local** API that runs on your machine (`localhost:5050`). It provides programmatic access to conversion functionality, allowing you to integrate the application into your own scripts, workflows, or pipelines.

## Important: Local-Only Architecture

**Key Point:** All conversions happen locally on your machine. No data is sent to external servers. This ensures complete privacy and security for your documents.

### Why Local-Only?

1. **Privacy**: Your documents never leave your machine.
2. **Security**: No internet connection required for conversions.
3. **Speed**: Direct file access without network overhead.
4. **Transparency**: As an open-source tool, you can verify how your data is handled.

### Architecture

```
┌─────────────────────────────────────┐
│   Desktop Application (PyQt6)      │
│   - UI for file selection           │
│   - Local config management         │
└────────┬────────────────────────────┘
         │
┌────────▼────────────────────────────┐
│   Local REST API (Flask)           │
│   - Runs on localhost:5050          │
│   - Optional API key auth           │
│   - REST endpoints for conversions  │
│   - Job tracking                    │
└────────┬────────────────────────────┘
         │
         │ (Local file system access only)
         │
┌────────▼────────────────────────────┐
│   Conversion Engines                │
│   - PIL/Pillow for images           │
│   - ReportLab for PDF generation    │
│   - PyMuPDF for PDF parsing         │
└─────────────────────────────────────┘
```

## API Endpoints

### Authentication

#### POST `/api/v1/auth/generate-key`
Generate an API key for local automation.

**Response:**
```json
{
  "api_key": "oss_xxxxxxxxxxxx",
  "message": "API key generated successfully. Keep it secure!"
}
```

### Health Check

#### GET `/api/v1/health`
Check API server status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.1.0-oss",
  "timestamp": "2026-05-08T10:30:00"
}
```

### Conversions

All conversion endpoints require the `X-API-Key` header with a valid API key.

#### POST `/api/v1/convert/images-to-pdf`
Convert multiple images into a single PDF.

**Headers:**
- `X-API-Key: oss_xxxxxxxxxxxx`

**Form Data:**
- `files`: Multiple image files (JPG, PNG, TIFF, BMP, WebP)
- `page_size`: "A4", "Letter", "Legal", or "Original" (optional, default: "A4")
- `output_name`: Output filename (optional, default: "output.pdf")

**Response:**
```json
{
  "success": true,
  "job_id": "abc123...",
  "message": "Conversion successful",
  "download_url": "/api/v1/download/abc123..."
}
```

#### POST `/api/v1/convert/pdf-to-images`
Convert PDF pages into individual images.

**Headers:**
- `X-API-Key: oss_xxxxxxxxxxxx`

**Form Data:**
- `file`: PDF file
- `format`: "jpg", "png", or "tiff" (optional, default: "jpg")
- `dpi`: Resolution (optional, default: 300)
- `page_numbers`: Comma-separated page numbers (optional, e.g., "1,3,5")

**Response:**
```json
{
  "success": true,
  "job_id": "def456...",
  "image_count": 3,
  "message": "Converted 3 pages",
  "download_url": "/api/v1/download/def456..."
}
```

### Job Management

#### GET `/api/v1/jobs/{job_id}`
Get job status and details.

**Headers:**
- `X-API-Key: oss_xxxxxxxxxxxx`

**Response:**
```json
{
  "type": "images_to_pdf",
  "status": "completed",
  "output_path": "/tmp/...",
  "created_at": "2026-05-08T10:30:00"
}
```

#### GET `/api/v1/download/{job_id}`
Download the conversion result.

**Headers:**
- `X-API-Key: oss_xxxxxxxxxxxx`

**Response:**
- Binary file download (PDF or images)

### Statistics

#### GET `/api/v1/stats`
Get API usage statistics.

**Headers:**
- `X-API-Key: oss_xxxxxxxxxxxx`

**Response:**
```json
{
  "total_jobs": 42,
  "active_api_keys": 1,
  "api_version": "1.1.0-oss"
}
```

## Usage Example (Python)

```python
import requests

# Ensure the desktop app is running or start the API server manually
API_BASE = "http://127.0.0.1:5050/api/v1"

# 1. Generate API key (one-time)
response = requests.post(f"{API_BASE}/auth/generate-key")
api_key = response.json()['api_key']

# 2. Convert images to PDF
files = {
    'files': [
        ('img1.jpg', open('img1.jpg', 'rb'), 'image/jpeg'),
        ('img2.jpg', open('img2.jpg', 'rb'), 'image/jpeg'),
    ]
}
data = {'page_size': 'A4'}
headers = {'X-API-Key': api_key}

response = requests.post(
    f"{API_BASE}/convert/images-to-pdf",
    files=files,
    data=data,
    headers=headers
)

print(response.json())
# {'success': True, 'job_id': '...', 'download_url': '...'}
```

## Security

### API Key Storage
- API keys are generated locally.
- Store API keys securely (environment variables, secrets manager).
- Never commit API keys to version control.

### Network Binding
- API binds **only to localhost (127.0.0.1)**.
- Not accessible from external networks.
- No inbound internet connections required.

## Implementation Details

**File:** `desktop-app/src/api/local_api.py`

**Key Components:**
- `LocalAPI` class: Main API server.
- Flask app: HTTP server.
- `ConversionEngine`: Handles actual conversions.

**Singleton Pattern:**
- `get_local_api()` returns the singleton instance.

## Troubleshooting

### Port Already in Use
The API tries to bind to port 5050. If this port is in use, you can specify a different port when starting the server:

```python
from src.api.local_api import get_local_api

api = get_local_api(port=5051)
api.start()
```

### Conversions Fail
- Check file formats (JPG, JPEG, PNG, TIFF, BMP, WebP).
- Ensure files are not corrupted.
- Check available disk space in your system's temp directory.
- Verify your API key is valid.
