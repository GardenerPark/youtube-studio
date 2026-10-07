# youtube-studio

유튜브 영상을 분석해서 대본·연출·음악 구조를 뽑고, 그 구조를 캡컷(CapCut PC) 드래프트로 바꾸는 파이프라인.

```
YouTube URL ──analyze_with_gemini.py──▶ scene_plan.json ──make_capcut_draft.py──▶ draft_out/
                                              │
                                              └─ (손으로 수정해도 됨, pipeline/schema.md 참고)
```

## 폴더

```
pipeline/
  analyze_with_gemini.py   # URL → scene_plan.json (+ analysis.md). Gemini API 키 필요
  make_capcut_draft.py     # scene_plan.json → CapCut 드래프트 폴더. 의존성 없음
  schema.md                # scene_plan.json 스키마
videos/
  L8OVETatbd0/             # 영상 ID별 폴더
    analysis.md            # 구조·대본 비트·연출·음악 큐 분석
    scene_plan.json        # 22샷 / 10 BGM / 23캡션 / 10타이틀
    draft_out/             # 생성된 draft_content.json, draft_meta_info.json
.env.example               # GEMINI_API_KEY=
```

## 1. 생성된 드래프트를 캡컷에서 열기

캡컷이 읽는 것은 `videos/<id>/draft_out/` 폴더뿐이다. PC용 캡컷(Windows/Mac)에서만 된다.

1. `draft_out` 폴더를 복사해 이름을 프로젝트명으로 바꾼다. 예: `jade_vlog_template`
2. 캡컷 드래프트 폴더 안에 넣는다. 탐색기/Finder 주소창에 붙여넣으면 열린다.
   ```
   Windows: %LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\
   macOS:   ~/Movies/CapCut/User Data/Projects/com.lveditor.draft/
   ```
3. 캡컷을 완전히 종료했다가 다시 실행하면 프로젝트 목록에 나타난다.
4. "미디어를 찾을 수 없음" 경고는 정상이다. 원본 영상을 받지 않았으므로 클립은 `PLACEHOLDER_s01.mp4` 같은 자리표시자다. 클립을 우클릭해 본인 촬영분으로 교체하거나, 자막·음악 큐 배치만 참고용으로 본다.

자리표시자 없이 바로 연결하려면 `s01.mp4`, `m01.mp3`처럼 id와 같은 이름의 파일을 한 폴더에 모아 두고 `--media-dir`로 넘긴다.

### 안 열릴 때

드래프트 포맷은 비공식이라 캡컷 버전에 따라 거부될 수 있다.

1. 캡컷에서 빈 프로젝트를 하나 새로 만든다.
2. 그 프로젝트 폴더의 `draft_content.json`에서 `platform`, `last_modified_platform`, `new_version`, `version` 값을 복사한다.
3. 생성된 `draft_content.json`의 같은 자리에 덮어쓴 뒤 캡컷을 재시작한다.

그래도 안 되면 캡컷 버전을 알려주면 그 값에 맞춰 `make_capcut_draft.py`의 `platform` 블록을 바꾸면 된다.

## 2. 드래프트 다시 만들기 (Python 3만 있으면 됨)

```bash
# scene_plan.json을 고친 뒤
python3 pipeline/make_capcut_draft.py videos/L8OVETatbd0/scene_plan.json videos/L8OVETatbd0/draft_out/

# 실제 클립을 연결하려면
python3 pipeline/make_capcut_draft.py videos/L8OVETatbd0/scene_plan.json videos/L8OVETatbd0/draft_out/ --media-dir /path/to/clips
```

같은 트랙 안에서 구간이 겹치면 에러로 멈춘다. 메시지에 겹친 시간이 나온다.

## 3. 다른 영상 분석하기 (Gemini API)

Gemini는 공개 YouTube URL을 바로 보고 영상+오디오 타임스탬프를 돌려준다.

```bash
pip install google-genai
cp .env.example .env     # GEMINI_API_KEY 채우기
export $(grep -v '^#' .env | xargs)

VID=영상ID
mkdir -p videos/$VID
python3 pipeline/analyze_with_gemini.py "https://www.youtube.com/watch?v=$VID" \
    videos/$VID/scene_plan.json --analysis videos/$VID/analysis.md
python3 pipeline/make_capcut_draft.py videos/$VID/scene_plan.json videos/$VID/draft_out/
```

- 비공개 영상은 안 된다. 공개 또는 일부공개여야 한다.
- 무료 키는 하루 영상 분 수에 제한이 있다. 23분짜리는 보통 들어간다.
- 긴 영상은 `--fps 0.5`로 토큰을 줄일 수 있다.

## 산출물 범위

- 비디오 1트랙, BGM 1트랙, 캡션 1트랙, 챕터 타이틀 1트랙. 트랜지션·키프레임·필터 LUT는 넣지 않는다. 흑백 샷에는 빈 필터 슬롯만 붙으므로 캡컷에서 필터를 고른다.
- 미디어 파일(mp4/mp3/jpg)은 gitignore되어 있다. 저장소에는 JSON과 문서만 올라간다.
