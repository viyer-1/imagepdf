"""
Local API - Programmatic access to conversion functionality.

This API runs locally on the user's machine and provides REST endpoints
to automate conversions. All processing remains local
and private - no data is sent to external servers.

Features:
- RESTful API for image/PDF conversions
- Optional API key authentication
- Batch processing
- Status monitoring
- Local-only (localhost binding for security)
"""

import secrets
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..core.converters import ConversionEngine
from ..utils import get_logger


class LocalAPI:
    """
    Local REST API for conversion automation.

    Security:
    - Binds only to localhost (127.0.0.1)
    - Optional API key authentication (can be disabled or self-generated)
    - All processing happens locally
    """

    def __init__(self, host="127.0.0.1", port=5050):
        """
        Initialize Local API server.

        Args:
            host: Host to bind to (default: 127.0.0.1 for security)
            port: Port to run on (default: 5050)
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.conversion_engine = ConversionEngine()
        self.logger = get_logger()

        # API key storage
        self.api_keys: Dict[str, Dict] = {}

        # Job tracking
        self.jobs: Dict[str, Dict] = {}

        # Server thread
        self._server_thread: Optional[threading.Thread] = None
        self._is_running = False

        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.route("/api/v1/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify(
                {"status": "healthy", "version": "1.1.0-oss", "timestamp": datetime.now().isoformat()}
            )

        @self.app.route("/api/v1/auth/generate-key", methods=["POST"])
        def generate_api_key():
            """Generate new API key for local automation."""
            # Generate secure API key - unlocked for everyone
            api_key = f"oss_{secrets.token_urlsafe(32)}"

            self.api_keys[api_key] = {
                "email": "local-user@oss",
                "created_at": datetime.now().isoformat(),
                "last_used": None,
            }

            return jsonify(
                {"api_key": api_key, "message": "API key generated successfully. Keep it secure!"}
            )

        @self.app.route("/api/v1/convert/images-to-pdf", methods=["POST"])
        def convert_images_to_pdf():
            """Convert images to PDF."""
            # Validate API Key
            api_key = request.headers.get("X-API-Key")
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401

            # Get parameters
            if "files" not in request.files:
                return jsonify({"error": "No files provided"}), 400

            files = request.files.getlist("files")
            page_size = request.form.get("page_size", "A4")
            output_name = request.form.get("output_name", "output.pdf")

            # Save uploaded files temporarily
            temp_dir = Path(tempfile.gettempdir()) / "local_api_uploads"
            temp_dir.mkdir(exist_ok=True)

            image_paths = []
            for file in files:
                if file.filename:
                    filename = secure_filename(file.filename)
                    filepath = temp_dir / filename
                    file.save(filepath)
                    image_paths.append(filepath)

            # Convert
            output_path = temp_dir / secure_filename(output_name)
            try:
                success = self.conversion_engine.images_to_pdf(image_paths, output_path, page_size)

                if success:
                    # Track job
                    job_id = secrets.token_hex(16)
                    self.jobs[job_id] = {
                        "type": "images_to_pdf",
                        "status": "completed",
                        "output_path": str(output_path),
                        "created_at": datetime.now().isoformat(),
                    }

                    return jsonify(
                        {
                            "success": True,
                            "job_id": job_id,
                            "message": "Conversion successful",
                            "download_url": f"/api/v1/download/{job_id}",
                        }
                    )
                else:
                    return jsonify({"error": "Conversion failed"}), 500

            except Exception as e:
                self.logger.error(f"API conversion error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/v1/convert/pdf-to-images", methods=["POST"])
        def convert_pdf_to_images():
            """Convert PDF to images."""
            api_key = request.headers.get("X-API-Key")
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401

            if "file" not in request.files:
                return jsonify({"error": "No PDF file provided"}), 400

            file = request.files["file"]
            output_format = request.form.get("format", "jpg")
            dpi = int(request.form.get("dpi", 300))
            page_numbers_str = request.form.get("page_numbers", None)

            # Parse page numbers if provided
            page_numbers = None
            if page_numbers_str:
                try:
                    page_numbers = [int(p.strip()) for p in page_numbers_str.split(",")]
                except ValueError:
                    return jsonify({"error": "Invalid page_numbers format"}), 400

            # Save PDF temporarily
            temp_dir = Path(tempfile.gettempdir()) / "local_api_uploads"
            temp_dir.mkdir(exist_ok=True)

            pdf_path = temp_dir / secure_filename(file.filename)
            file.save(pdf_path)

            # Convert
            output_dir = temp_dir / f"output_{secrets.token_hex(8)}"
            output_dir.mkdir(exist_ok=True)

            try:
                image_paths = self.conversion_engine.pdf_to_images(
                    pdf_path, output_dir, output_format, dpi, page_numbers
                )

                job_id = secrets.token_hex(16)
                self.jobs[job_id] = {
                    "type": "pdf_to_images",
                    "status": "completed",
                    "output_files": [str(p) for p in image_paths],
                    "created_at": datetime.now().isoformat(),
                }

                return jsonify(
                    {
                        "success": True,
                        "job_id": job_id,
                        "image_count": len(image_paths),
                        "message": f"Converted {len(image_paths)} pages",
                        "download_url": f"/api/v1/download/{job_id}",
                    }
                )

            except Exception as e:
                self.logger.error(f"API conversion error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/v1/jobs/<job_id>", methods=["GET"])
        def get_job_status(job_id):
            """Get job status."""
            api_key = request.headers.get("X-API-Key")
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401

            if job_id not in self.jobs:
                return jsonify({"error": "Job not found"}), 404

            return jsonify(self.jobs[job_id])

        @self.app.route("/api/v1/download/<job_id>", methods=["GET"])
        def download_result(job_id):
            """Download conversion result."""
            api_key = request.headers.get("X-API-Key")
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401

            if job_id not in self.jobs:
                return jsonify({"error": "Job not found"}), 404

            job = self.jobs[job_id]

            if job["type"] == "images_to_pdf":
                output_path = Path(job["output_path"])
                if output_path.exists():
                    return send_file(output_path, as_attachment=True)
            elif job["type"] == "pdf_to_images":
                # For multiple images, return info (in production, could zip them)
                return jsonify(
                    {
                        "files": job["output_files"],
                        "note": "Use individual file endpoints to download images",
                    }
                )

            return jsonify({"error": "Output file not found"}), 404

        @self.app.route("/api/v1/stats", methods=["GET"])
        def get_stats():
            """Get API usage statistics."""
            api_key = request.headers.get("X-API-Key")
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401

            return jsonify(
                {
                    "total_jobs": len(self.jobs),
                    "active_api_keys": len(self.api_keys),
                    "api_version": "1.0.0",
                }
            )

    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not api_key or api_key not in self.api_keys:
            return False

        # Update last used timestamp
        self.api_keys[api_key]["last_used"] = datetime.now().isoformat()
        return True

    def start(self, threaded=True):
        """
        Start the API server.

        Args:
            threaded: Run in separate thread (default: True)
        """
        if self._is_running:
            self.logger.warning("API server already running")
            return

        self._is_running = True
        self.logger.info(f"Starting Local API server on {self.host}:{self.port}")

        if threaded:
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()
        else:
            self._run_server()

    def _run_server(self):
        """Run the Flask server."""
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    def stop(self):
        """Stop the API server."""
        self._is_running = False
        self.logger.info("Local API server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._is_running

    def get_api_url(self) -> str:
        """Get the base API URL."""
        return f"http://{self.host}:{self.port}/api/v1"


# Singleton instance
_local_api_instance: Optional[LocalAPI] = None


def get_local_api(host="127.0.0.1", port=5050) -> LocalAPI:
    """
    Get singleton instance of Local API.

    Args:
        host: Host to bind to (default: localhost for security)
        port: Port to run on

    Returns:
        LocalAPI instance
    """
    global _local_api_instance
    if _local_api_instance is None:
        _local_api_instance = LocalAPI(host, port)
    return _local_api_instance
