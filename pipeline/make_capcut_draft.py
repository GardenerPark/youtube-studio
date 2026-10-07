#!/usr/bin/env python3
"""
make_capcut_draft.py  —  scene_plan.json  ->  CapCut (PC) draft folder

Usage:
    python3 make_capcut_draft.py scene_plan.json draft_out/ [--media-dir /abs/path/to/clips]

The output folder contains `draft_content.json` and `draft_meta_info.json`.
Copy the whole folder into CapCut's draft directory and restart CapCut:

    Windows: %LOCALAPPDATA%\\CapCut\\User Data\\Projects\\com.lveditor.draft\\
    macOS:   ~/Movies/CapCut/User Data/Projects/com.lveditor.draft/

Every media reference is a placeholder (PLACEHOLDER_<shot id>.mp4 / .mp3)
unless --media-dir is given, in which case files named <shot id>.* found there
are linked instead. CapCut shows "media missing" for placeholders; right-click
the clip and relink it to your own footage.

No third-party dependencies. The draft format is undocumented and may change
between CapCut versions; see README for the recovery steps if a draft refuses
to open.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

US = 1_000_000  # CapCut stores every time value in microseconds

# Fonts bundled with CapCut that work for Korean + Latin text. Any name that is
# not installed silently falls back to the default font inside CapCut.
STYLE_FONTS = {
    "serif": "SourceHanSerifKR-Regular",
    "sans": "SourceHanSansKR-Regular",
    "handwritten": "NanumPen",
    "mono": "DejaVuSansMono",
}


def uid() -> str:
    return str(uuid.uuid4()).upper()


def us(sec: float) -> int:
    return int(round(float(sec) * US))


def hex_to_rgb(color: str) -> list[float]:
    color = color.lstrip("#")
    return [int(color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]


# --------------------------------------------------------------------------- #
# material builders
# --------------------------------------------------------------------------- #
def video_material(path: str, name: str, duration_us: int, width: int, height: int) -> dict:
    return {
        "aigc_type": "none",
        "audio_fade": None,
        "cartoon_path": "",
        "category_id": "",
        "category_name": "local",
        "check_flag": 63,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": duration_us,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "has_audio": True,
        "height": height,
        "id": uid(),
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": "",
        "material_id": "",
        "material_name": name,
        "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False,
                    "interactiveTime": [], "path": "", "strokes": []},
        "media_path": "",
        "object_locked": None,
        "origin_material_id": "",
        "path": path,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0, "time_range": {"duration": 0, "start": 0}},
        "team_id": "",
        "type": "video",
        "video_algorithm": {"algorithms": [], "complement_frame_config": None, "deflicker": None,
                            "gameplay_configs": [], "motion_blur_config": None, "noise_reduction": None,
                            "path": "", "quality_enhance": None, "time_range": None},
        "width": width,
    }


def audio_material(path: str, name: str, duration_us: int) -> dict:
    return {
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "duration": duration_us,
        "effect_id": "",
        "formula_id": "",
        "id": uid(),
        "intensifies_path": "",
        "local_material_id": "",
        "music_id": uid(),
        "name": name,
        "path": path,
        "query": "",
        "request_id": "",
        "resource_id": "",
        "search_id": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "type": "extract_music",
        "video_id": "",
        "wave_points": [],
    }


def text_material(text: str, *, size: float, color: str, font: str, align: int, bold: bool) -> dict:
    content = {
        "styles": [{
            "fill": {"content": {"solid": {"color": hex_to_rgb(color)}}},
            "font": {"id": "", "path": ""},
            "size": size,
            "bold": bold,
            "range": [0, len(text)],
        }],
        "text": text,
    }
    return {
        "add_type": 0,
        "alignment": align,
        "background_alpha": 1.0,
        "background_color": "",
        "background_height": 0.14,
        "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0,
        "background_style": 0,
        "background_vertical_offset": 0.0,
        "background_width": 0.14,
        "bold_width": 0.0,
        "border_alpha": 1.0,
        "border_color": "",
        "border_width": 0.08,
        "caption_template_info": {"category_id": "", "category_name": "", "effect_id": "",
                                  "is_new": False, "path": "", "request_id": "", "resource_id": "",
                                  "resource_name": "", "source_platform": 0},
        "check_flag": 7,
        "combo_info": {"text_templates": []},
        "content": json.dumps(content, ensure_ascii=False),
        "fixed_height": -1.0,
        "fixed_width": -1.0,
        "font_category_id": "",
        "font_category_name": "",
        "font_id": "",
        "font_name": font,
        "font_path": "",
        "font_resource_id": "",
        "font_size": size,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": "none",
        "font_url": "",
        "fonts": [],
        "force_apply_line_max_width": False,
        "global_alpha": 1.0,
        "group_id": "",
        "has_shadow": False,
        "id": uid(),
        "initial_scale": 1.0,
        "inner_padding": -1.0,
        "is_rich_text": False,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "line_feed": 1,
        "line_max_width": 0.82,
        "line_spacing": 0.02,
        "multi_language_current": "none",
        "name": "",
        "original_size": [],
        "preset_category": "",
        "preset_category_id": "",
        "preset_has_set_alignment": False,
        "preset_id": "",
        "preset_index": 0,
        "preset_name": "",
        "recognize_task_id": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.9,
        "shadow_angle": -45.0,
        "shadow_color": "",
        "shadow_distance": 5.0,
        "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
        "shadow_smoothing": 0.45,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "style_name": "",
        "sub_type": 0,
        "subtitle_keywords": None,
        "subtitle_template_original_fontsize": 0.0,
        "text_alpha": 1.0,
        "text_color": color,
        "text_curve": None,
        "text_preset_resource_id": "",
        "text_size": 30,
        "text_to_audio_ids": [],
        "tts_auto_update": False,
        "type": "text",
        "typesetting": 0,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {"end_time": [], "start_time": [], "text": []},
    }


def speed_material() -> dict:
    return {"curve_speed": None, "id": uid(), "mode": 0, "speed": 1.0, "type": "speed"}


def canvas_material() -> dict:
    return {"album_image": "", "blur": 0.0, "color": "", "id": uid(), "image": "",
            "image_id": "", "image_name": "", "source_platform": 0, "team_id": "", "type": "canvas_color"}


def sound_channel_material() -> dict:
    return {"audio_channel_mapping": 0, "id": uid(), "is_config_open": False, "type": ""}


def filter_material(name: str) -> dict:
    # A named filter slot. CapCut needs its own effect_id/path for a real LUT;
    # we leave those empty so the editor shows the slot and the user picks one.
    return {"adjust_params": [], "algorithm_artifact_path": "", "apply_target_type": 0,
            "bloom_params": None, "category_id": "", "category_name": "", "color_match_info": None,
            "effect_id": "", "enable_skin_tone_correction": False, "exclusion_group": [],
            "face_adjust_params": [], "formula_id": "", "id": uid(), "intensity_key": "",
            "multi_language_current": "", "name": name, "panel_id": "", "path": "",
            "platform": "all", "request_id": "", "resource_id": "", "source_platform": 0,
            "sub_type": "none", "time_range": None, "type": "filter", "value": 1.0,
            "version": ""}


# --------------------------------------------------------------------------- #
# segment builders
# --------------------------------------------------------------------------- #
def base_segment(material_id: str, start_us: int, dur_us: int, extra_refs: list[str],
                 *, render_index: int = 0, volume: float = 1.0, src_start_us: int = 0) -> dict:
    return {
        "cartoon": False,
        "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False}, "rotation": 0.0,
                 "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}},
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_curves": True,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": extra_refs,
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": uid(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": material_id,
        "render_index": render_index,
        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0, "size_layout": 0,
                              "target_follow": "", "vertical_pos_layout": 0},
        "reverse": False,
        "source_timerange": {"duration": dur_us, "start": src_start_us},
        "speed": 1.0,
        "target_timerange": {"duration": dur_us, "start": start_us},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": volume,
    }


def text_segment(material_id: str, start_us: int, dur_us: int, extra_refs: list[str],
                 *, y: float, scale: float, render_index: int) -> dict:
    seg = base_segment(material_id, start_us, dur_us, extra_refs, render_index=render_index)
    seg["clip"]["transform"] = {"x": 0.0, "y": y}
    seg["clip"]["scale"] = {"x": scale, "y": scale}
    seg["uniform_scale"] = {"on": True, "value": scale}
    return seg


def track(kind: str, segments: list[dict], name: str = "", flag: int = 0) -> dict:
    return {"attribute": 0, "flag": flag, "id": uid(), "is_default_name": not bool(name),
            "name": name, "segments": segments, "type": kind}


# --------------------------------------------------------------------------- #
# plan validation
# --------------------------------------------------------------------------- #
def check_no_overlap(items: list[dict], label: str) -> None:
    prev_end = -1.0
    for it in sorted(items, key=lambda d: d["start"]):
        if it["end"] <= it["start"]:
            sys.exit(f"[{label}] '{it.get('id', it.get('text'))}' has end <= start")
        if it["start"] < prev_end - 1e-6:
            sys.exit(f"[{label}] overlap at {it['start']}s (previous ended {prev_end}s). "
                     f"Items on one track must not overlap.")
        prev_end = it["end"]


def resolve_media(media_dir: Path | None, item_id: str, exts: tuple[str, ...], placeholder_ext: str) -> str:
    if media_dir:
        for ext in exts:
            cand = media_dir / f"{item_id}{ext}"
            if cand.exists():
                return str(cand.resolve())
    return f"PLACEHOLDER_{item_id}{placeholder_ext}"


# --------------------------------------------------------------------------- #
# main build
# --------------------------------------------------------------------------- #
def build(plan: dict, media_dir: Path | None) -> tuple[dict, dict]:
    canvas = plan.get("canvas", {})
    width = int(canvas.get("width", 1920))
    height = int(canvas.get("height", 1080))
    fps = float(canvas.get("fps", 30))
    total_us = us(plan["duration_sec"])

    shots = sorted(plan.get("shots", []), key=lambda d: d["start"])
    music = sorted(plan.get("music", []), key=lambda d: d["start"])
    subtitles = sorted(plan.get("subtitles", []), key=lambda d: d["start"])
    titles = sorted(plan.get("titles", []), key=lambda d: d["start"])
    check_no_overlap(shots, "shots")
    check_no_overlap(music, "music")
    check_no_overlap(subtitles, "subtitles")
    check_no_overlap(titles, "titles")

    m = {k: [] for k in (
        "audio_balances", "audio_effects", "audio_fades", "audios", "beats", "canvases", "chromas",
        "color_curves", "digital_humans", "drafts", "effects", "flowers", "green_screens", "handwrites",
        "hsl", "images", "log_color_wheels", "loudnesses", "manual_deformations", "masks",
        "material_animations", "material_colors", "multi_language_refs", "placeholders",
        "plugin_effects", "primary_color_wheels", "realtime_denoises", "shapes", "smart_crops",
        "smart_relights", "sound_channel_mappings", "speeds", "stickers", "tail_leaders",
        "text_templates", "texts", "time_marks", "transitions", "video_effects", "video_trackings",
        "videos", "vocal_separations")}

    # ---- video track -------------------------------------------------------
    video_segs = []
    for s in shots:
        dur = us(s["end"]) - us(s["start"])
        path = resolve_media(media_dir, s["id"], (".mp4", ".mov", ".MP4", ".MOV"), ".mp4")
        vm = video_material(path, os.path.basename(path), dur, width, height)
        sp, cv, sc = speed_material(), canvas_material(), sound_channel_material()
        m["videos"].append(vm); m["speeds"].append(sp); m["canvases"].append(cv)
        m["sound_channel_mappings"].append(sc)
        refs = [sp["id"], cv["id"], sc["id"]]
        if s.get("grade") == "bw":
            flt = filter_material("Black & White (apply manually)")
            m["effects"].append(flt)
            refs.append(flt["id"])
        seg = base_segment(vm["id"], us(s["start"]), dur, refs, volume=float(s.get("volume", 1.0)))
        video_segs.append(seg)

    # ---- music track -------------------------------------------------------
    audio_segs = []
    for cue in music:
        dur = us(cue["end"]) - us(cue["start"])
        path = resolve_media(media_dir, cue["id"], (".mp3", ".wav", ".m4a"), ".mp3")
        am = audio_material(path, os.path.basename(path), dur)
        sp, sc = speed_material(), sound_channel_material()
        m["audios"].append(am); m["speeds"].append(sp); m["sound_channel_mappings"].append(sc)
        fade = {"fade_in_duration": us(cue.get("fade_in", 0.0)),
                "fade_out_duration": us(cue.get("fade_out", 0.0)),
                "fade_type": 0, "id": uid(), "type": "audio_fade"}
        m["audio_fades"].append(fade)
        seg = base_segment(am["id"], us(cue["start"]), dur, [sp["id"], sc["id"], fade["id"]],
                           volume=float(cue.get("volume", 0.5)))
        audio_segs.append(seg)

    # ---- subtitle track ----------------------------------------------------
    sub_style = plan.get("subtitle_style", {})
    sub_font = STYLE_FONTS.get(sub_style.get("font", "sans"), sub_style.get("font", "sans"))
    sub_segs = []
    for i, sub in enumerate(subtitles):
        dur = us(sub["end"]) - us(sub["start"])
        tm = text_material(sub["text"], size=float(sub_style.get("size", 7)),
                           color=sub_style.get("color", "#FFFFFF"), font=sub_font, align=1, bold=False)
        m["texts"].append(tm)
        sub_segs.append(text_segment(tm["id"], us(sub["start"]), dur, [],
                                     y=float(sub_style.get("y", -0.78)), scale=1.0, render_index=14000 + i))

    # ---- chapter title track ----------------------------------------------
    title_segs = []
    for i, t in enumerate(titles):
        dur = us(t["end"]) - us(t["start"])
        font = STYLE_FONTS.get(t.get("style", "serif"), t.get("style", "serif"))
        tm = text_material(t["text"], size=float(t.get("size", 12)), color=t.get("color", "#FFFFFF"),
                           font=font, align=1, bold=bool(t.get("bold", False)))
        m["texts"].append(tm)
        title_segs.append(text_segment(tm["id"], us(t["start"]), dur, [],
                                       y=float(t.get("y", 0.0)), scale=1.0, render_index=15000 + i))

    now = int(time.time() * US)
    platform = {"app_id": 359289, "app_source": "cc", "app_version": "5.9.0", "device_id": "",
                "hard_disk_id": "", "mac_address": "", "os": "windows", "os_version": "10.0"}
    draft = {
        "canvas_config": {"height": height, "ratio": "original", "width": width},
        "color_space": 0,
        "config": {"adjust_max_index": 1, "attachment_info": [], "combination_max_index": 1,
                   "export_range": None, "extract_audio_last_index": 1, "lyrics_recognition_id": "",
                   "lyrics_sync": True, "lyrics_taskinfo": [], "maintrack_adsorb": True,
                   "material_save_mode": 0, "multi_language_current": "none", "multi_language_list": [],
                   "multi_language_main": "none", "multi_language_mode": "none", "original_sound_last_index": 1,
                   "record_audio_last_index": 1, "sticker_max_index": 1, "subtitle_keywords_config": None,
                   "subtitle_recognition_id": "", "subtitle_sync": True, "subtitle_taskinfo": [],
                   "system_font_list": [], "video_mute": False, "zoom_info_params": None},
        "cover": None,
        "create_time": now,
        "duration": total_us,
        "extra_info": None,
        "fps": fps,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": uid(),
        "keyframe_graph_list": [],
        "keyframes": {"adjusts": [], "audios": [], "effects": [], "filters": [], "handwrites": [],
                      "stickers": [], "texts": [], "videos": []},
        "last_modified_platform": platform,
        "materials": m,
        "mutable_config": None,
        "name": plan.get("project_name", plan.get("title", "")),
        "new_version": "110.0.0",
        "platform": platform,
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [
            track("video", video_segs),
            track("audio", audio_segs, name="BGM"),
            track("text", sub_segs, name="Subtitles"),
            track("text", title_segs, name="Chapter titles"),
        ],
        "update_time": now,
        "version": 360000,
    }

    meta = {
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_materials": [],
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "draft_cover.jpg",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {"draft_enterprise_extra": "", "draft_enterprise_id": "",
                                  "draft_enterprise_name": "", "enterprise_material": []},
        "draft_fold_path": "",
        "draft_id": draft["id"],
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_invisible": False,
        "draft_materials": [],
        "draft_materials_copied_info": [],
        "draft_name": draft["name"],
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": "",
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": 0,
        "draft_type": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_create": now,
        "tm_draft_modified": now,
        "tm_draft_removed": 0,
        "tm_duration": total_us,
    }
    return draft, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene_plan", help="scene_plan.json produced by analyze_with_gemini.py or by hand")
    ap.add_argument("out_dir", help="draft folder to create (becomes the CapCut project folder)")
    ap.add_argument("--media-dir", help="folder with <shot id>.mp4 / <cue id>.mp3 to link instead of placeholders")
    args = ap.parse_args()

    plan = json.loads(Path(args.scene_plan).read_text(encoding="utf-8"))
    media_dir = Path(args.media_dir) if args.media_dir else None
    draft, meta = build(plan, media_dir)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "draft_content.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "draft_meta_info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    n_shots = len(draft["tracks"][0]["segments"])
    n_music = len(draft["tracks"][1]["segments"])
    n_subs = len(draft["tracks"][2]["segments"])
    n_titles = len(draft["tracks"][3]["segments"])
    print(f"wrote {out/'draft_content.json'}")
    print(f"  duration {plan['duration_sec']}s | shots {n_shots} | music cues {n_music} | "
          f"subtitles {n_subs} | titles {n_titles}")
    if media_dir is None:
        print("  media: placeholders only (use --media-dir to link real clips)")


if __name__ == "__main__":
    main()
