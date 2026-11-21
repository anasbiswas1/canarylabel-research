import json

import pools


def test_read_rows_formats(tmp_path):
    rows = [{"text": "a", "label": 0}, {"text": "b", "label": 1}]
    (tmp_path / "l.json").write_text(json.dumps(rows))
    (tmp_path / "d.json").write_text(json.dumps({"meta": {"n": 2}, "records": rows}))
    (tmp_path / "j.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    for name in ("l.json", "d.json", "j.jsonl"):
        assert pools.read_rows(tmp_path / name) == rows


def test_shared_rows_routes_labels():
    b, i = pools.shared_rows("liu_bipia_pairs", [{"text": "clean", "label": 0, "suite": "bipia-email", "task": "email/test/1"},
                                                 {"text": "attack", "label": 1, "suite": "bipia-email", "task": "email/test/1",
                                                  "attack": "bipia:x"}])
    assert len(b) == 1 and len(i) == 1 and b[0]["host"] == i[0]["host"] == "bipia-email/email/test/1"
    b, i = pools.shared_rows("picalib_agentdojo", [{"text": "slot", "label": 1, "suite": "banking", "slot": "v"}])
    assert b == [] and i == []
    b, i = pools.shared_rows("structural_test", [{"text": "x", "label": 1, "form": "embedded", "host_src": "h"},
                                                 {"text": "y", "label": 0, "form": "declarative_insert", "host_src": "h"}])
    assert len(i) == 1 and len(b) == 1 and b[0]["host"] == "structural/h"


def test_finalise_dedupes_and_excludes():
    rows = [{"source": "s", "text": "Same  text"}, {"source": "t", "text": "same text"}, {"source": "s", "text": "attack"}]
    out = pools.finalise(rows, exclude_texts={"attack"})
    assert len(out) == 1 and len(out[0]["doc_id"]) == 16
