# scene_plan.json 스키마

`analyze_with_gemini.py`가 만들고 `make_capcut_draft.py`가 읽는 중간 포맷입니다.
손으로 고쳐도 됩니다. 시간 값은 전부 **초 단위 숫자**(예: `83.5`)입니다.

```jsonc
{
  "video_id": "L8OVETatbd0",
  "source_url": "https://www.youtube.com/watch?v=L8OVETatbd0",
  "title": "영상 제목",
  "channel": "채널명",
  "project_name": "캡컷 프로젝트 이름",          // draft name
  "duration_sec": 1380,                          // 전체 길이
  "canvas": { "width": 1920, "height": 1080, "fps": 30 },
  "subtitle_style": { "font": "sans", "size": 6, "color": "#FFFFFF", "y": -0.78 },

  "shots": [                                     // 비디오 트랙 (겹침 금지)
    { "id": "s01", "start": 0, "end": 11,
      "label": "장면 이름", "shot_type": "저각 POV", "location": "런던",
      "grade": "color | bw | mixed",             // bw 이면 필터 슬롯이 붙음
      "volume": 1.0,                             // 선택, 클립 원음 볼륨
      "notes": "조명·전환·사운드 메모" }
  ],
  "music": [                                     // BGM 트랙 (겹침 금지, 빈 구간 허용)
    { "id": "m01", "start": 11, "end": 34,
      "genre": "팝", "mood": "에너지", "volume": 0.8,
      "duck_under_narration": false,
      "fade_in": 0.0, "fade_out": 0.0, "notes": "" }
  ],
  "subtitles": [                                 // 캡션/자막 텍스트 트랙
    { "start": 4, "end": 7, "text": "hello" }
  ],
  "titles": [                                    // 챕터 타이틀/전면 카드 텍스트 트랙
    { "start": 34, "end": 38, "text": "archived by JADE SIM",
      "style": "serif | sans | handwritten | mono",
      "size": 12, "color": "#FFFFFF", "bold": false, "y": 0.0 }
  ],

  "script_beats": [ ... ],                       // 선택, Gemini가 채움. 드래프트에는 안 들어감
  "structure_summary": "..."                     // 선택
}
```

## 미디어 매핑

드래프트의 각 클립은 `PLACEHOLDER_<id>.mp4`, 각 BGM은 `PLACEHOLDER_<id>.mp3`를 가리킵니다.
`--media-dir` 폴더에 `s01.mp4`, `m01.mp3`처럼 id와 같은 이름의 파일을 두면
자리표시자 대신 실제 경로가 들어갑니다.

## 트랙 배치

| 트랙 | 소스 키 | 캡컷 트랙 타입 |
|---|---|---|
| 1 | `shots` | video |
| 2 | `music` | audio (이름 "BGM") |
| 3 | `subtitles` | text (이름 "Subtitles") |
| 4 | `titles` | text (이름 "Chapter titles") |

같은 트랙 안에서 구간이 겹치면 `make_capcut_draft.py`가 에러로 멈춥니다.
