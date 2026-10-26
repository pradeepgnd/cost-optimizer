"""Separate loopback ingestion process; bucket credentials never enter the application runtime."""
from pathlib import Path
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.adapters.live_zetaris import ZetarisDataLayer
from app.adapters.base import require_env
from app.source_contracts import SourceBindings, StorageConfig
from app.source_registry import EvidencePublisher
from app.source_snapshots import json_load


def ingest_handler(publisher, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path != "/evidence":
                self.send_error(404)
                return
            if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}"):
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    self.send_error(413)
                    return
                record = json_load(self.rfile.read(length))
                source = publisher.write(record)
                body = json.dumps({"source": source.model_dump(mode="json")}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as error:
                # Never include storage credentials, server bodies or founder text in HTTP errors.
                body = json.dumps({"status": "not_published", "error_type": type(error).__name__}).encode()
                self.send_response(409 if isinstance(error, ValueError) else 503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-dotenv", action="store_true")
    args = parser.parse_args()
    if not args.no_dotenv:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    config = StorageConfig.model_validate_json(args.storage.read_text())
    bindings = SourceBindings.model_validate_json(args.bindings.read_text())
    token = require_env("SOURCE_INGEST_TOKEN")
    # One shared HTTP client is thread-safe; evidence writes also use a publisher lock and S3 CAS.
    layer = ZetarisDataLayer(bindings=bindings)
    publisher = EvidencePublisher(layer, config, bindings)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ingest_handler(publisher, token))
    print(json.dumps({"status": "listening", "url": f"http://127.0.0.1:{server.server_port}", "storage": config.backend}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        layer.client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
