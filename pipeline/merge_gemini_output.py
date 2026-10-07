#!/usr/bin/env python3
"""
merge_gemini_output.py  —  raw Gemini JSON (web app or API)  ->  valid scene_plan.json

Usage:
    python3 merge_gemini_output.py scene_plan_gemini.json scene_plan.json [--video-id ID] [--url URL]

Fills in the wrapper fields make_capcut_draft.py expects (video_id, canvas,
subtitle_style, project_name), strips a stray ```json fence if the text was
copied from a chat window, converts "mm:ss" strings to seconds, clamps
overlaps inside each list, and extends the last shot to duration_sec.
If an existing scene_plan.json is given as the output path, its video_id /
source_url / canvas are kept.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def to_sec(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    parts = s.split(":")
    if len(parts) in (2, 3) and all(p.replace(".", "", 1).isdigit() for p in parts):
        parts = [float(p) for p in parts]
        return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
    return float(s)


def load_loose_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        sys.exit(f"{path}: no JSON object found")
    return json.loads(text[start:end + 1])


def fix_list(items: list[dict], prefix: str | None) -> list[dict]:
    for i, it in enumerate(items):
        it["start"] = to_sec(it["start"])
        it["end"] = to_sec(it["end"])
        if prefix and not it.get("id"):
            it["id"] = f"{prefix}{i + 1:02d}"
    items.sort(key=lambda d: d["start"])
    for prev, cur in zip(items, items[1:]):
        if cur["start"] < prev["end"]:
            prev["end"] = cur["start"]
    return [it for it in items if it["end"] > it["start"]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gemini_json")
    ap.add_argument("out")
    ap.add_argument("--video-id")
    ap.add_argument("--url")
    args = ap.parse_args()

    raw = load_loose_json(Path(args.gemini_json))
    out_path = Path(args.out)
    prev = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    vid = args.video_id or prev.get("video_id") or raw.get("video_id") or "video"
    url = args.url or prev.get("source_url") or raw.get("source_url") or f"https://www.youtube.com/watch?v={vid}"

    plan = {
        "video_id": vid,
        "source_url": url,
        "title": raw.get("title", prev.get("title", "")),
        "channel": raw.get("channel", prev.get("channel", "")),
        "project_name": prev.get("project_name", f"{vid}_template"),
        "duration_sec": to_sec(raw.get("duration_sec") or prev.get("duration_sec") or 0),
        "canvas": prev.get("canvas", {"width": 1920, "height": 1080, "fps": 30}),
        "subtitle_style": prev.get("subtitle_style", {"font": "sans", "size": 6, "color": "#FFFFFF", "y": -0.78}),
        "structure_summary": raw.get("structure_summary", ""),
        "script_beats": fix_list(raw.get("script_beats", []), None),
        "shots": fix_list(raw.get("shots", []), "s"),
        "music": fix_list(raw.get("music", []), "m"),
        "subtitles": fix_list(raw.get("subtitles", []), None),
        "titles": fix_list(raw.get("titles", []), None),
    }
    if not plan["duration_sec"] and plan["shots"]:
        plan["duration_sec"] = plan["shots"][-1]["end"]
    if plan["shots"] and plan["shots"][-1]["end"] < plan["duration_sec"]:
        plan["shots"][-1]["end"] = plan["duration_sec"]
    for s in plan["shots"]:
        s.setdefault("grade", "color")
        if s["grade"] not in ("color", "bw", "mixed"):
            s["grade"] = "color"
    for t in plan["titles"]:
        if t.get("style") not in ("serif", "sans", "handwritten", "mono"):
            t["style"] = "serif"

    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}: {len(plan['shots'])} shots, {len(plan['music'])} music, "
          f"{len(plan['subtitles'])} captions, {len(plan['titles'])} titles, "
          f"{len(plan['script_beats'])} beats, duration {plan['duration_sec']}s")


if __name__ == "__main__":
    main()
