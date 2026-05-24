"""One-off: extract microsoft_form.json from agent transcript."""

import json
import re
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\samif\.cursor\projects\c-Users-samif-OneDrive-Desktop-Hate-Crime-Tracking-Form"
    r"\agent-transcripts\db1b481d-8aa5-4b5c-bb4a-a6724ee2e29b"
    r"\db1b481d-8aa5-4b5c-bb4a-a6724ee2e29b.jsonl"
)
OUT = Path(__file__).resolve().parent.parent / "data" / "microsoft_form.json"


def main() -> None:
    for line in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
        if "rbcce8666b2ef4952bf3d47b5b59500b7" not in line:
            continue
        obj = json.loads(line)
        text = obj["message"]["content"][0]["text"]
        start = text.find("[")
        if start < 0:
            raise SystemExit("JSON array not found")
        raw = text[start:]
        decoder = json.JSONDecoder()
        data, end = decoder.raw_decode(raw)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {len(data)} items to {OUT}")
        return
    raise SystemExit("Transcript line not found")


if __name__ == "__main__":
    main()
