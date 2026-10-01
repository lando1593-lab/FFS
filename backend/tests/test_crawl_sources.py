import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from ffs.sources.crawl import crawl, merge_into_registry

PAGES = {
    "/": b'<html><a href="/products">Products</a> <a href="/private/secret.pdf">x</a> '
    b'<a href="https://iq.ulprospector.com/x">UL</a></html>',
    "/products": b'<html><a href="/docs/CAFCO-400_C-TDS.pdf">CAFCO 400 TDS</a> '
    b'<a href="/docs/primers.PDF">Approved primer list</a> <a href="/products">self</a> '
    b'<a href="/deep">deep</a></html>',
    "/deep": b'<html><a href="/deeper">deeper</a></html>',
    "/deeper": b'<html><a href="/docs/thickness-chart.xlsx">UL design thickness chart</a> '
    b'<a href="/download/pds/55">Product Data Sheet</a> <a href="/about">About</a></html>',
    "/download/pds/55": b"%PDF-1.4 extensionless data sheet",
    "/robots.txt": b"User-agent: *\nDisallow: /private/\n",
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_HEAD(self):
        body = PAGES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/pdf" if body.startswith(b"%PDF") else "text/html"
        )
        self.end_headers()

    def do_GET(self):
        body = PAGES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header(
            "Content-Type", "text/plain" if self.path == "/robots.txt" else "text/html"
        )
        self.end_headers()
        self.wfile.write(body)


def test_crawl_discovers_documents_within_rules():
    srv = HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}/"
        rep = crawl(
            [base], ["127.0.0.1"], max_pages=50, max_depth=2, delay_s=0, sleep=lambda s: None
        )
        urls = sorted(d.url for d in rep.documents)
        assert urls == [
            f"{base}docs/CAFCO-400_C-TDS.pdf",
            f"{base}docs/primers.PDF",
        ]  # /deeper is beyond depth 2
        assert "iq.ulprospector.com" in rep.skipped_hosts
        assert not any("private" in d.url for d in rep.documents)
        tds = next(d for d in rep.documents if "TDS" in d.url)
        assert tds.manufacturer_guess == "Isolatek" and tds.kind_guess == "product_data"
        assert tds.found_on == f"{base}products" and tds.link_text == "CAFCO 400 TDS"
        reg = {"allowed_hosts": ["127.0.0.1"], "sources": []}
        assert merge_into_registry(rep, reg) == 2
        assert merge_into_registry(rep, reg) == 0  # idempotent
        assert reg["sources"][0]["status"] == "discovered"
        rep3 = crawl(
            [base], ["127.0.0.1"], max_pages=50, max_depth=3, delay_s=0, sleep=lambda s: None
        )
        assert any(
            d.url.endswith("thickness-chart.xlsx") and d.kind_guess == "design_listing"
            for d in rep3.documents
        )
    finally:
        srv.shutdown()
