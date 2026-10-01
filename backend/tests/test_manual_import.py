import json
from datetime import UTC, datetime

from ffs.sources.manual import import_manual, manual_items, write_manual_list


def _registry(tmp_path):
    reg = {
        "allowed_hosts": ["example.com"],
        "sources": [
            {
                "id": "acme-ul-x100-aaaaaa",
                "manufacturer": "Acme",
                "product": "Firestuff",
                "kind": "design_listing",
                "url": None,
                "status": "robots_disallowed",
                "manual_url": "https://dam.example.com/d/1/original?content-type=application%2Fpdf&name=UL+X100+%28Column%29.pdf",
                "file_name": "UL X100 (Column).pdf",
            },
            {
                "id": "acme-notes-only-bbbbbb",
                "manufacturer": "Acme",
                "kind": "product_data",
                "url": None,
                "notes": "NOT FETCHED: challenge page. Save manually: https://dam.example.com/d/2?name=Data+Sheet.pdf",
            },
            {
                "id": "acme-fetched-cccccc",
                "manufacturer": "Acme",
                "url": "https://example.com/a.pdf",
            },
        ],
    }
    p = tmp_path / "acme.json"
    p.write_text(json.dumps(reg))
    return p


def test_manual_items_and_list(tmp_path):
    reg = _registry(tmp_path)
    items = manual_items([reg])
    assert [i.id for i in items] == ["acme-ul-x100-aaaaaa", "acme-notes-only-bbbbbb"]
    assert items[0].file_name == "UL X100 (Column).pdf"
    assert items[1].file_name == "Data Sheet.pdf"  # from the name= query parameter
    assert items[1].manual_url == "https://dam.example.com/d/2?name=Data+Sheet.pdf"
    html_path, csv_path = write_manual_list(items, tmp_path / "out")
    page = html_path.read_text()
    assert "UL X100 (Column).pdf" in page and "href='https://dam.example.com/d/1/" in page
    assert csv_path.read_text().count("\n") == 3


def test_import_manual_files_matches_and_reports_unmatched(tmp_path):
    reg = _registry(tmp_path)
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "UL X100 (Column).pdf").write_bytes(b"%PDF-1.4 x100")
    (drop / "data sheet.PDF").write_bytes(b"%PDF-1.4 ds")  # case/punctuation-insensitive match
    (drop / "something-else.pdf").write_bytes(b"%PDF-1.4 ?")
    lib = tmp_path / "lib"
    lib.mkdir()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    results, unmatched = import_manual(drop, [reg], lib, now=now)
    assert unmatched == ["something-else.pdf"]
    assert [r.status for r in results] == ["manual", "manual"]
    assert results[0].stored_path.startswith("Acme/acme-ul-x100-aaaaaa/")
    assert results[0].url.startswith("https://dam.example.com/d/1/")
    rows = [json.loads(line) for line in (lib / "manifest.jsonl").read_text().splitlines()]
    assert rows[0]["method"] == "manual" and rows[0]["drop_file"] == "UL X100 (Column).pdf"
    assert rows[0]["fetched_at"] == now.isoformat()
    assert (lib / results[0].stored_path).read_bytes() == b"%PDF-1.4 x100"
    # importing the same file again is "unchanged" and does not duplicate the stored copy
    results2, _ = import_manual(drop, [reg], lib, now=now)
    assert results2[0].status == "unchanged" and results2[0].stored_path == results[0].stored_path
    assert len(list((lib / "Acme" / "acme-ul-x100-aaaaaa").iterdir())) == 1
