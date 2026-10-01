import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from ffs.sources.fetch import fetch_all


class H(BaseHTTPRequestHandler):
    body = b"%PDF-1.4 fake data sheet"
    etag = '"v1"'

    def log_message(self, *a):  # silence
        pass

    def do_GET(self):
        if self.path == "/robots.txt":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /private/\n")
            return
        if self.path.startswith("/private/"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"secret")
            return
        if self.headers.get("If-None-Match") == H.etag:
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("ETag", H.etag)
        self.send_header("Last-Modified", "Wed, 01 Jan 2025 00:00:00 GMT")
        self.end_headers()
        self.wfile.write(H.body)


def test_fetch_registry_rules(tmp_path):
    srv = HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        reg = {
            "allowed_hosts": ["127.0.0.1"],
            "sources": [
                {
                    "id": "ok-doc",
                    "manufacturer": "Test Co",
                    "url": f"http://127.0.0.1:{port}/tds.pdf",
                },
                {"id": "no-url", "manufacturer": "Test Co", "url": None},
                {
                    "id": "bad-host",
                    "manufacturer": "Test Co",
                    "url": "http://iq.ulprospector.com/x",
                },
                {
                    "id": "robots",
                    "manufacturer": "Test Co",
                    "url": f"http://127.0.0.1:{port}/private/x.pdf",
                },
            ],
        }
        lib = tmp_path / "lib"
        r1 = {r.id: r for r in fetch_all(lib, reg)}
        assert r1["ok-doc"].status == "fetched" and r1["ok-doc"].changed is False
        assert (lib / r1["ok-doc"].stored_path).read_bytes() == H.body
        assert r1["ok-doc"].stored_path.startswith("Test_Co/ok-doc/")
        assert r1["no-url"].status == "skipped_no_url"
        assert r1["bad-host"].status == "refused_host"
        assert r1["robots"].status == "robots_disallow"
        # second run: conditional request → unchanged, no new file
        r2 = {r.id: r for r in fetch_all(lib, reg)}
        assert r2["ok-doc"].status == "unchanged" and r2["ok-doc"].http_status == 304
        assert len(list((lib / "Test_Co" / "ok-doc").iterdir())) == 1
        # content change → new file stored, flagged changed
        H.body = b"%PDF-1.4 revised data sheet"
        H.etag = '"v2"'
        r3 = {r.id: r for r in fetch_all(lib, reg)}
        assert r3["ok-doc"].status == "fetched" and r3["ok-doc"].changed is True
        assert len(list((lib / "Test_Co" / "ok-doc").iterdir())) == 2
        lines = [json.loads(x) for x in (lib / "manifest.jsonl").read_text().splitlines()]
        assert sum(1 for x in lines if x["id"] == "ok-doc") == 3
    finally:
        srv.shutdown()


def test_sniff_extension_from_magic_bytes():
    from ffs.sources.fetch import _sniff_extension

    assert _sniff_extension(b"%PDF-1.7 ...") == ".pdf"
    assert _sniff_extension(b"PK\x03\x04" + b"x" * 10 + b"word/document.xml") == ".docx"
    assert _sniff_extension(b"PK\x03\x04" + b"x" * 10 + b"xl/workbook.xml") == ".xlsx"
    assert _sniff_extension(b"PK\x03\x04" + b"nothing") == ".zip"
    assert _sniff_extension(b"<html>") is None
