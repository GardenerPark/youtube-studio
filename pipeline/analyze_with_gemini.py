#!/usr/bin/env python3
"""
analyze_with_gemini.py  —  YouTube URL  ->  scene_plan.json  (+ analysis.md)

Gemini can take a public YouTube URL as a file part and watch video + audio
together, returning timestamps. This script asks it for a structured scene
plan in the schema described in pipeline/schema.md so the result can be fed
straight into make_capcut_draft.py.

Usage:
    pip install google-genai
    export GEMINI_API_KEY=...            # or put it in .env and `source` it
    python3 analyze_with_gemini.py "https://www.youtube.com/watch?v=VIDEO_ID" scene_plan.json
    python3 analyze_with_gemini.py URL scene_plan.json --analysis analysis.md --model gemini-2.5-pro

Notes:
  * Only public (or unlisted) videos work; private videos are rejected by the API.
  * Free-tier keys cap daily YouTube video minutes; a 23-minute video usually
    fits, longer ones may need a paid key.
  * Long videos are sampled at 1 fps by default. Pass --fps 0.5 to halve the
    token cost on a very long video, or --fps 2 for finer cuts on a short one.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("google-genai is not installed. Run: pip install google-genai")

TIME_ITEM = {
    "type": "OBJECT",
    "properties": {
        "start": {"type": "NUMBER", "description": "seconds from video start"},
        "end": {"type": "NUMBER", "description": "seconds from video start, > start"},
    },
}

def _with(base: dict, extra: dict, required: list[str]) -> dict:
    out = json.loads(json.dumps(base))
    out["properties"].update(extra)
    out["required"] = required
    return out

SCENE_PLAN_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "channel": {"type": "STRING"},
        "duration_sec": {"type": "NUMBER"},
        "structure_summary": {"type": "STRING", "description": "3-6 sentences on overall structure"},
        "script_beats": {
            "type": "ARRAY",
            "items": _with(TIME_ITEM, {
                "beat": {"type": "STRING", "description": "one-sentence summary of what is said"},
                "key_quote": {"type": "STRING", "description": "verbatim line in the spoken language"},
            }, ["start", "end", "beat"]),
        },
        "shots": {
            "type": "ARRAY",
            "items": _with(TIME_ITEM, {
                "id": {"type": "STRING", "description": "s01, s02, ..."},
                "label": {"type": "STRING"},
                "shot_type": {"type": "STRING", "description": "framing / camera: POV, talking head, wide, low angle, close-up ..."},
                "location": {"type": "STRING"},
                "grade": {"type": "STRING", "enum": ["color", "bw", "mixed"]},
                "notes": {"type": "STRING", "description": "lighting, transition in/out, sound design"},
            }, ["id", "start", "end", "label", "shot_type", "grade"]),
        },
        "music": {
            "type": "ARRAY",
            "items": _with(TIME_ITEM, {
                "id": {"type": "STRING", "description": "m01, m02, ..."},
                "genre": {"type": "STRING"},
                "mood": {"type": "STRING"},
                "volume": {"type": "NUMBER", "description": "0-1 relative level under narration"},
                "duck_under_narration": {"type": "BOOLEAN"},
                "fade_in": {"type": "NUMBER"},
                "fade_out": {"type": "NUMBER"},
                "notes": {"type": "STRING"},
            }, ["id", "start", "end", "genre", "volume", "duck_under_narration"]),
        },
        "subtitles": {
            "type": "ARRAY",
            "description": "on-screen captions / lower thirds exactly as shown",
            "items": _with(TIME_ITEM, {"text": {"type": "STRING"}}, ["start", "end", "text"]),
        },
        "titles": {
            "type": "ARRAY",
            "description": "chapter title cards and full-screen text cards",
            "items": _with(TIME_ITEM, {
                "text": {"type": "STRING"},
                "style": {"type": "STRING", "enum": ["serif", "sans", "handwritten", "mono"]},
                "size": {"type": "NUMBER"},
                "color": {"type": "STRING", "description": "#RRGGBB"},
                "bold": {"type": "BOOLEAN"},
            }, ["start", "end", "text", "style"]),
        },
    },
    "required": ["title", "duration_sec", "structure_summary", "script_beats", "shots", "music", "subtitles", "titles"],
}

PROMPT = """You are a senior video editor reverse-engineering this YouTube video so it can be
rebuilt as a CapCut template. Watch the whole video, including audio.

Return a scene plan with:
- script_beats: 8-20 beats summarising the narration in order, each with a verbatim key quote
  in the original spoken language.
- shots: 15-40 contiguous, NON-overlapping shots covering 0 to the full duration. For each,
  give camera framing, location, color grade (color / bw / mixed), and notes on lighting,
  the cut or transition into the next shot, and diegetic sound.
- music: every background music cue, NON-overlapping, with exact start/end in seconds,
  genre, mood, a relative volume 0-1, whether it ducks under narration, and fades.
  Leave gaps where there is no music. Note hard stops / tape-stop effects.
- subtitles: every on-screen caption or lower third, exact text, when it appears/disappears.
- titles: every chapter title card or full-screen text card, exact text, and a font style guess.

Timestamps are seconds from the start as numbers (e.g. 83.5), never mm:ss strings.
Items within one list must not overlap. Be precise rather than round."""


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else "video"


def fix_overlaps(items: list[dict]) -> list[dict]:
    """Clamp any accidental overlaps so make_capcut_draft.py accepts the plan."""
    items = sorted(items, key=lambda d: d["start"])
    for prev, cur in zip(items, items[1:]):
        if cur["start"] < prev["end"]:
            prev["end"] = cur["start"]
    return [it for it in items if it["end"] > it["start"]]


def write_analysis(plan: dict, path: Path, url: str) -> None:
    def ts(sec: float) -> str:
        sec = int(round(sec)); return f"{sec // 60:02d}:{sec % 60:02d}"
    lines = [f"# {plan.get('title', '')}", "", f"- 채널: {plan.get('channel', '')}", f"- URL: {url}",
             f"- 길이: {ts(plan['duration_sec'])}", "", "## 구조", "", plan.get("structure_summary", ""), "",
             "## 대본 비트", "", "| 시간 | 요지 | 핵심 대사 |", "|---|---|---|"]
    for b in plan.get("script_beats", []):
        lines.append(f"| {ts(b['start'])}–{ts(b['end'])} | {b['beat']} | {b.get('key_quote', '')} |")
    lines += ["", "## 샷 리스트", "", "| ID | 시간 | 장면 | 샷 타입 | 장소 | 그레이드 | 메모 |", "|---|---|---|---|---|---|---|"]
    for s in plan["shots"]:
        lines.append(f"| {s['id']} | {ts(s['start'])}–{ts(s['end'])} | {s['label']} | {s['shot_type']} | "
                     f"{s.get('location', '')} | {s['grade']} | {s.get('notes', '')} |")
    lines += ["", "## 음악 큐", "", "| ID | 시간 | 장르 | 무드 | 볼륨 | 더킹 | 메모 |", "|---|---|---|---|---|---|---|"]
    for mcue in plan["music"]:
        lines.append(f"| {mcue['id']} | {ts(mcue['start'])}–{ts(mcue['end'])} | {mcue['genre']} | {mcue.get('mood', '')} | "
                     f"{mcue['volume']} | {'예' if mcue['duck_under_narration'] else '아니오'} | {mcue.get('notes', '')} |")
    lines += ["", "## 타이틀 카드", ""] + [f"- {ts(t['start'])} `{t['text']}` ({t['style']})" for t in plan["titles"]]
    lines += ["", "## 화면 캡션", ""] + [f"- {ts(c['start'])} `{c['text']}`" for c in plan["subtitles"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="public YouTube watch URL")
    ap.add_argument("out", help="where to write scene_plan.json")
    ap.add_argument("--analysis", help="also write a markdown analysis to this path")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"))
    ap.add_argument("--fps", type=float, default=None, help="video sampling rate (default: API default, 1 fps)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("Set GEMINI_API_KEY (see .env.example)")

    client = genai.Client()
    video_part_kwargs = {"file_data": types.FileData(file_uri=args.url, mime_type="video/mp4")}
    if args.fps:
        video_part_kwargs["video_metadata"] = types.VideoMetadata(fps=args.fps)
    contents = types.Content(role="user", parts=[types.Part(**video_part_kwargs), types.Part(text=PROMPT)])

    print(f"asking {args.model} to watch {args.url} ...", file=sys.stderr)
    resp = client.models.generate_content(
        model=args.model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCENE_PLAN_SCHEMA,
            temperature=0.2,
        ),
    )
    plan = json.loads(resp.text)

    vid = video_id(args.url)
    plan = {
        "video_id": vid,
        "source_url": args.url,
        "project_name": f"{vid}_template",
        "canvas": {"width": args.width, "height": args.height, "fps": 30},
        "subtitle_style": {"font": "sans", "size": 6, "color": "#FFFFFF", "y": -0.78},
        **plan,
    }
    for key in ("shots", "music", "subtitles", "titles"):
        plan[key] = fix_overlaps(plan.get(key, []))
    if plan["shots"]:
        plan["shots"][-1]["end"] = max(plan["shots"][-1]["end"], plan["duration_sec"])

    Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out}: {len(plan['shots'])} shots, {len(plan['music'])} music cues, "
          f"{len(plan['subtitles'])} captions, {len(plan['titles'])} titles", file=sys.stderr)
    if args.analysis:
        write_analysis(plan, Path(args.analysis), args.url)
        print(f"wrote {args.analysis}", file=sys.stderr)


if __name__ == "__main__":
    main()
