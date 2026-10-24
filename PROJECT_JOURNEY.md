# IELTS Speaking Trainer -- Project Journey & Architecture Summary

> Generated 2026-10-24. This document captures the full scope of decisions, architecture, and lessons learned across the entire project lifecycle.

---

## 1. Project Overview

**Repository:** `github.com:nyatskr/ielts-speaking-trainer` (single `main` branch, GitHub Pages from root)
**Live URL:** `https://nyatskr.github.io/ielts-speaking-trainer/`
**Tech stack:** Pure static HTML/CSS/JS. No framework, no build step, no backend, no npm dependencies.
**Total tracked files:** 75 (8 code files + 66 audio + 1 JSON), 251 MB repo.

### Current page inventory

| File | Size | Role | Status |
|---|---|---|---|
| `index.html` | 12 KB | Portfolio hub: 3 project cards (Speaking / Listening / Writing / Studio) | Evolving |
| `speaking.html` | 312 KB | **Frozen** speaking case study: click-to-play with forced alignment | **Never touch again** |
| `listening.html` | 20 KB | Dictation mode: sentence-level replay with word-level diff | Evolving |
| `writing.html` | 55 KB | Writing Lab: IELTS essay scoring with LLM (BYOK + demo mode) | Evolving |
| `writing-data.js` | 96 KB | 28 essay tasks, rubric, 2 demo corrections, system prompt | Evolving |
| `listening-data.js` | 226 KB | 64 topics, 2,491 sentences, block timestamps | Evolving |
| `studio.html` | 53 KB | Voice Studio: per-sentence TTS synthesis (browser/Azure/Doubao) | Evolving |
| `audio_p1/` | 38 files | Part 1 audio (Whisper-aligned) | Frozen |
| `audio_p23/` | 28 files | Part 2&3 audio (Whisper-aligned) | Frozen |
| `timestamps.json` | 1 file | Whisper forced alignment timestamps | Frozen |

### Adjacent project (same workspace)

| `linux-practice-site/` | ~496 KB | 360-question Red Hat Linux practice site (static, no backend) | Evolving |

---

## 2. Commit History (chronological)

| Commit | Date | Summary |
|---|---|---|
| `98858cd` | 10-22 | Initial: static site with forced-alignment click-to-play |
| `57e0332` | 10-23 | Add Writing Lab, split portfolio, dedupe topics (66 to 64) |
| `061ba50` | 10-23 | Add limitations + reflection block to speaking page |
| `620f9a4` | 10-23 | Make speaking self-contained; split model answers into paragraphs |
| `abbe3be` | 10-23 | Add dictation mode: sentence-level replay with word-level diff |
| `5407379` | 10-23 | Split dictation into listening.html; freeze speaking.html; add hub |
| `62bff19` | 10-23 | Merge listening hero and drill panel into one dark block |
| `1db4144` | 10-23 | Add browser-only voice studio: per-sentence TTS, skip alignment |
| `81ad680` | 10-23 | Add zero-setup browser voice engine to the studio |
| `528dc94` | 10-24 | Fix studio voice loading: poll, live resolve at playback, status UI |

---

## 3. Architecture: Speaking Page (the core case study)

### The problem it solves
IELTS speaking practice requires audio that plays each line on click. The naive approach -- cut each sentence into its own audio file -- destroys the natural rhythm (gaps, hesitations, examiner-candidate handoff). The solution: keep the full audio track and recover per-line timing after the fact.

### Pipeline
```
Full audio (mp3, 30-90s per topic)
    |
    v
Whisper forced alignment  (word-level timestamps)
    |
    v
timestamps.json  { "topic_NN.mp3": [ [0.00, 3.20], [3.20, 7.85], ... ] }
    |
    v
speaking.html: click a line -> audio.currentTime = ts[i][0] -> play until ts[i][1]
```

### Key data structures
- `P1_DATA`: 36 Part 1 topics, 274 questions. Each topic: `{ num, name, blocks: [text, ...], src: "audio_p1/topic_NN.mp3" }`
- `P23_DATA`: 28 Part 2&3 topics. Each topic: `{ num, name, cue_main, cue_bullets, p2, blocks: [text, ...], src: "audio_p23/topic_NN.mp3" }`
- `TS` (now in `listening-data.js`): `{ "topic_NN.mp3": [[start, end], ...] }` -- block-level timestamps from Whisper

### Deduplication
Original data had 66 topics but 2 were duplicates (Work or Studies / Home and Accommodation). Removed and renumbered to 64 unique topics. `P23_DATA` has no `src` field; path derived from `num` via `srcFor()`. `P1_DATA` has explicit `src` field because of a renumber remap (num 23 -> topic_24.mp3, skipping deleted 23/26).

### Interaction model
- Block-level click-to-play (not word-level -- word timestamps were too noisy)
- Mutex: only one block plays at a time
- Auto-advance to next block on end
- localStorage progress: `ielts_part1_done_v1` / `ielts_p23_done_v1`
- SVG infographic explains the pipeline (in `.principle` block)

### Why it was frozen
User explicitly required a pure speaking link for a class presentation. No dictation, no studio, no external links. `speaking.html` was rolled back to commit `620f9a4` and declared permanently frozen. Any new features go into separate pages.

---

## 4. Architecture: Listening / Dictation Page

### What it does
Sentence-level dictation: play one sentence, user types what they hear, get word-by-word comparison.

### Key design decisions
- **Sentence-level, not block-level**: Median question length is 9 words (max 20) -- ideal for whole-sentence dictation. Median answer length is 47 words (max 196) -- too long, must be split.
- **Timestamps are block-level only**, so sentence-level timing is linearly interpolated by character count within each block's [start, end] interval. TTS speed is nearly constant, so the interpolation error is negligible.
- **Word comparison**: LCS dynamic programming, then adjacent miss/extra pairs are reclassified as "wrong word" (the user typed something, just not the right word).
- **Three-state display**: `ok` (green), `miss` (orange dashed = omitted word), `bad` (red solid = wrong word, hover shows what you typed). Extra words listed separately.
- **Progress**: localStorage `ielts_dict_v1`.

### Gotchas fixed
1. **Curly quotes**: Script data uses U+2019 (`'`), but the word-splitting regex only matched ASCII `'`. All contractions (`I'm`, `don't`) were split wrong. Fix: normalize `\u2018\u2019\u02bc` to ASCII `'` before splitting.
2. **First-play seek dropped**: `preload="none"` audio element has `readyState=0`; setting `currentTime` is silently ignored. Fix: seek+play immediately (same path as block jump), then self-correct on `loadedmetadata`.
3. **Headless test got wrong audio element**: `querySelector('audio')` grabbed the demo area's audio. Must filter by `src`.

---

## 5. Architecture: Writing Lab

### What it does
IELTS essay scoring with an LLM. Two modes:
- **Demo mode**: Pre-generated correction JSON (zero setup, works offline)
- **BYOK mode**: User provides an API key to any OpenAI-compatible endpoint (DeepSeek, Kimi, Qwen, GLM, OpenAI). Key stored in localStorage.

### Data model
- `TASKS`: 28 essay tasks from Simon's PDF. Each: `{ id, type (XY/XYZ), title, prompt, model (full band-9 essay), why (short qualitative description) }`
- `RUBRIC`: TR/CC/LR/GRA band 5-8 descriptors (public version)
- `DEMOS`: 2 complete pre-generated corrections (9-paragraph output format)
- `SYS_PROMPT`: 6-step scoring framework + JSON output schema

### Scoring
- Total = average of 4 dimensions, rounded to nearest 0.5 per IELTS rules
- Local fallback: when no API key, the AI drawer matches keywords in the user's text to pre-generated correction JSON -- not a dead end

### Data sourcing
- Model essays extracted from Simon's band-9 essay PDF (annotated edition, 28 essays) using PyMuPDF `get_text("blocks")`
- Paragraph splitting by vertical gap between blocks (threshold = 16; intra-paragraph gap 3.7-8.2, inter-paragraph gap 21-41)
- Critical constraint: `DEMOS.errors[].original` matches by exact substring, so the essay text cannot be altered at all. Only `\n\n` separators are inserted at sentence boundaries closest to the PDF's paragraph breaks. Assertion: `ns(new) == ns(old)` for all 28 essays.

---

## 6. Architecture: Voice Studio

### The problem it replaces
The speaking page depends on pre-generated audio (Whisper alignment). If you change a script, you must re-run the entire alignment pipeline (Python + Whisper + ffmpeg, hours). The studio eliminates this by synthesizing each sentence as its own audio clip -- duration is known at synthesis time, no alignment needed.

### Three TTS providers

| Provider | CORS | Export | Setup | Quality |
|---|---|---|---|---|
| **Browser built-in** (`speechSynthesis`) | N/A | Cannot capture to file | Zero | Edge: neural en-GB (Sonia/Ryan); Chrome: eSpeak-based (flat) |
| **Azure TTS** | Allowed (`*`) | mp3 blob | API key (F0 = 500K chars/mo free) | Best (neural, same as Edge) |
| **Doubao/ByteDance** | Blocked | mp3 blob | API key + proxy needed | Good (neural) |

### Key architectural insight
**`speechSynthesis` audio cannot be captured to a file.** It writes directly to the audio device, bypassing the Web Audio node graph. `MediaRecorder` + `createMediaStreamDestination()` yields empty audio. Only `getDisplayMedia` works (manual, non-batchable). Therefore:
- **Local mode = listening only** (no export)
- **Azure/Doubao = exportable mp3** (via fetch, returns Blob)

### Data scale
- 64 topics / 1,024 blocks / 2,491 sentences / 196,017 characters
- = 39% of Azure free monthly quota
- Speaker detection: Part 1 uses `bi % 2` (547 consistent / 1 exception); Part 2&3 uses "first block ending with `?`" as Part 3 start

### Cache
- IndexedDB: database `voice-studio`, store `clips`
- Cache key = `provider|voice|speed|text`
- Changing one sentence only re-synthesizes that sentence

### Export
- Hand-written store-only ZIP (CRC32 + local header + central directory + EOCD, UTF-8 names via flag 0x0800)
- Verified with `unzip -t`
- `listening.html` can consume `manifest.json` + `seg/*.mp3` from the studio for higher-precision sentence playback

### Voice loading bug (commit `528dc94`)

**Symptom**: Dropdowns showed "No en-GB voices found", pronunciation sounded robotic/mechanical.

**Root cause chain**:
1. `speechSynthesis.getVoices()` is asynchronous in Chromium: returns `[]` at page parse time, populates ~1s later via `voiceschanged` event
2. Old code read the list once at parse time and cached the empty array
3. When playback started before voices arrived, `u.voice` was never set
4. Browser fell back to system default voice (non-en-GB, robotic)
5. Additionally: Windows has no en-GB voice installed at OS level (only zh-CN + en-US Zira); Edge's en-GB neural voices come via Edge's cloud voice service
6. `readCfg()` wiped saved voice choice when select held the placeholder (value="")

**Fix**:
- Poll every 500ms for 10s, then slow safety poll every 3s
- Both `addEventListener("voiceschanged")` + `onvoiceschanged`
- `liveVoiceFor()` re-reads `getVoices()` at playback time, never trusts cached array
- `rankVoices()`: neural/Online-Natural voices first, en-GB before en-*
- Visible status readout + "Reload voices" / "Test examiner" / "Test candidate" buttons
- Safe `readCfg()` that doesn't overwrite saved choice with empty string
- Honest error in log when no voice available, instead of playing garbage

---

## 7. Architecture: Linux Practice Site (adjacent project)

### What it does
360-question Red Hat Linux practice exam site. Static, no build, no dependencies. Works from `file://` without a server.

### Key design decisions
- **No Vite/React**: Classic script with `window.LINUX_BANK` injected. Double-click `index.html` to use.
- Question bank embedded as JS (not fetched JSON) because `file://` fetch fails on CORS
- 14 topics / 360 questions (199 single-choice + 161 multi-choice) / 65 clusters
- `knowledge_point` is nearly 1:1 with questions, so the topic page uses **clusters** (65) as the primary unit, expanding to kp capsules only when a cluster has multiple knowledge points
- Shuffle is disabled (`display_policy.shuffle_options = false`) so option letters A-D are stable
- Progress: localStorage `lp.progress.v1`; mastery = last attempt correct AND `wrongCount == 0`
- Import merges (not clears), previews new/merged/skipped, takes newer `answeredAt` and max `wrongCount`

### Explanation replacement
Original explanations were poor quality. User provided a 360-item Markdown analysis document. A `tools/build-bank.py` parser:
- Parses `## / ### / ####` three-level structure
- Extracts per-option analysis (`A | correct/wrong | reason`), notes, version, learning level, source refs
- Validates: question count, option count, answer match, analysis item order, version/level/source key
- Writes back to `bank.js` idempotently

### Testing
CDP (Chrome DevTools Protocol) over native WebSocket (Node 22, zero dependencies):
- 41 assertions across explanation-specific + full-site regression + file:// mode
- Must use `Network.setCacheDisabled` or stale JS is served
- Must use `?fresh=<timestamp>` after clearing localStorage to force real reload
- `Page.navigate` to same-URL-different-hash does NOT reload the page

---

## 8. Submission Format (academic context)

**Course**: Professional English midterm assignment
**Requirements**: Individual work, all-English, 4 options (poster / video / single-page interactive webpage / online portfolio), submit URL, 8-10 min English presentation + 5 min Q&A.

**Decision**: Submit as **Form 3 (single-page interactive technical webpage)**.
- Link: `speaking.html` (the frozen speaking page)
- Rationale: single page, interactive audio, SVG infographic, zero-dependency demo (no API key/network needed), 8-10 min fits one pipeline story, eliminates the "two technologies" debate (speaking + writing are different tech)
- Writing module demoted to "other work" on portfolio page, not part of this submission
- `speaking.html` has 0 external links (intentional) -- it is a standalone single-page work

---

## 9. Cross-cutting Lessons

### CSS gotchas
- `.field { display: flex }` overrides `[hidden]` UA style. Must add `.field[hidden] { display: none !important }`
- Class name collision: `.lab` was used by both a paragraph tag and the page layout. Always grep before naming new components
- `1fr` = `minmax(auto, 1fr)` -- the auto minimum is `min-content`, which can blow up the viewport. Use `minmax(0, 1fr)` to allow shrinking
- `.otext` (button text) needs `min-width: 0` + `overflow-wrap: anywhere` to prevent content from forcing horizontal overflow

### Headless testing
- Chrome headless minimum viewport is 512px; `--window-size=390` renders at 512 then crops
- `--screenshot` requires absolute paths; relative paths silently fail
- `--user-data-dir` with relative path produces 0-byte screenshots
- `--virtual-time-budget` does not wait for sub-resources (iframes, etc.)
- Inject test hooks by writing state into `document.title`, then read via `--dump-dom | grep <title>`
- For IIFE-wrapped scripts: simulate real clicks on real controls, don't call internal functions

### Audio
- `preload="none"` audio element silently ignores `currentTime` when `readyState = 0`
- `speechSynthesis` output bypasses Web Audio graph; cannot be captured via `MediaRecorder`
- Whisper alignment is word-level but too noisy for word-level click-to-play; block-level is the practical granularity

### Data
- PDF batch-annotated text: use `get_text("blocks")` and inter-block vertical gap for paragraph recovery. Don't try semantic splitting.
- When text must be preserved exactly (for substring matching), only insert separators (`\n\n`) and assert `no_whitespace(new) == no_whitespace(old)`
- Escaping: all user-facing text goes through `esc()` or `textContent`; backtick-wrapped content becomes `<code>` after escaping

### Git
- GitHub Pages has a 2-4 minute build delay after push; don't panic and change config
- `.git/config` remote URL with embedded PAT is a leak risk -- revoke if the zip was shared

---

## 10. Pending / Backlog

### IELTS project
- [ ] iFlytek pronunciation assessment for read-along recording (BYOK, WebSocket + HMAC)
- [ ] Add selected listening sets from `xiahua-listening-win.zip` (228 sets, 1.74 GB -- too large for Pages, needs CDN or selective inclusion)
- [ ] Speaking page AI assistant drawer (BYOK, similar to writing page)
- [ ] Azure F0 resource setup for natural en-GB TTS export in studio

### Linux practice site
- [ ] (Interrupted) Replace 360-question explanations from the user-supplied Markdown analysis doc -- was already done once, user interrupted a second pass

### Hard constraints (must not violate)
- `speaking.html` is **frozen** at 312 KB. Never add features to it.
- All shipped files must have **CJK = 0** (including comments)
- Audio generation must be executable on different devices (no Python/Whisper/ffmpeg dependency for end users)
- Project must remain **backendless** (static site on GitHub Pages only)
