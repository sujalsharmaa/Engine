# Python Video Studio

**You provide:** a voiceover + one JSON file. **You get:** a finished video (visuals, SFX, music ducking, word-highlight captions, camera motion, colour grade).

```
topic ──LLM──▶ storyboard.json ─┐
                                ├─▶ python run_studio.py ──▶ output/video.mp4
script text ──record──▶ vo.mp3 ─┘
```

## Quick start
```bash
pip install -r requirements.txt            # + ffmpeg, cairo/pango (see Dockerfile)
python -m engine.docgen                    # regenerate docs/ (optional)

python run_studio.py --script examples/gallery_9x16.json --quality preview      # no audio needed: silent preview
python run_studio.py --script my_video.json --audio voiceover.mp3               # final 1080p
python run_studio.py --script my_video.json --audio vo.mp3 --music assets/music/bg.mp3
python run_studio.py --script my_video.json --check                             # validate only
```
Docker: `docker build -t studio . && docker run --rm -v "$PWD":/studio studio --script my.json --audio vo.mp3`

## Workflow
1. Paste `docs/LLM_SYSTEM_PROMPT.md` into your LLM, give it a topic -> it returns the JSON (`narration_text` per scene).
2. Record/TTS the voiceover by reading all `narration_text` in order.
3. `run_studio.py --script x.json --audio vo.mp3`.

**No timestamps anywhere.** Scene boundaries, every `trigger_keyword` reveal and every caption word are located in the audio
automatically (Whisper + sequence alignment against your script, so mis-heard words don't break timing).

## What changed vs. the original engine
| Area | Before | Now |
|---|---|---|
| Timing | hand-written start/end per scene, fixed animation lengths | derived from the voiceover; all animations scheduled on the audio timeline |
| Components | 8 (B-tree was unfinished and crashed) | **23**, registry-based, 16:9 + 9:16 + 1:1 layouts |
| Adding a visual | edit compiler + renderer + schema | one class in `engine/components/` |
| Validation | crash mid-render | schema errors with scene/field names before rendering; typo warnings |
| Icons | 3 SVGs, fetched over network | 2,154 Lucide + 167 brand logos bundled offline |
| Audio | fixed music volume, `amix` shrinking the voice | sidechain ducking, `normalize=0`, loudness -14 LUFS, more SFX |
| Post | OpenCV -> mp4v -> libx264 (2 lossy encodes) | single pass: camera, bloom, vignette, grain, progress bar, captions |
| Captions | none | word-highlight (`pop`) or `line`, from script text |
| Iteration | full render every time | `--quality preview`, render cache keyed on storyboard + engine source |

## Components (details: `docs/COMPONENTS.md`)
Intro/outro: **TitleCard, HeroQuoteHook, KineticText, CallToAction** · Lists: **KeyPointsList, ProsCons, ProcessSteps, Timeline, MindMap**
Data: **BigStat, BarChart, LineChart, DonutChart, ComparisonTable** · Cards: **TiltedCardComparison, FeatureCarouselCards**
Tech: **MacOSCodeWindow** (syntax highlight, diff, step spotlight), **TerminalTyping, ArchitectureFlowCanvas, HexMemoryInspector, BTreeCameraZoom, RetroCrashDialog** · Media: **ImageShowcase**

Scene options: `transition` fade|slide|zoom|wipe|cut, `camera` static|push_in|pull_out|drift.
Video options: `aspect_ratio` 16:9|9:16|1:1, `studio_theme` (8 palettes incl. light), `captions` off|pop|line, `background` grid|plain|spotlight_only.

## Adding a component
```python
@register
class Quote2(Component):
    name = "Quote2"; description = "..."; best_for = "..."
    class Spec(VisualSpec):
        component_type: Literal["Quote2"] = "Quote2"
        text: str
    example = {"component_type": "Quote2", "text": "Hi"}
    example_narration = "Hi there."
    def render(self):
        c = self.ctx                      # geometry, theme, time API
        t = c.T(self.v.text, 40)
        c.at(c.cue_times([self.v.exact_time])[0], FadeIn(t))
        c.hold()
```
Then `python -m engine.docgen` and `pytest -q`. Items inside lists can inherit `Cue` to get `trigger_keyword` for free.

## Layout of the repo
`engine/components/*` visuals · `engine/timing.py` audio alignment · `engine/context.py` geometry + time API ·
`engine/post_processor.py` audio mix + finishing · `engine/captions.py` ASS captions · `engine/docgen.py` docs ·
`examples/` galleries of every component · `tests/`

## Tips
* Scene too short for its animations? The render prints a `timing drift` warning naming the scene — shorten items or lengthen narration.
* Images for `ImageShowcase` go next to the script or in `assets/images/`.
* Put music in `assets/music/`; it is ducked automatically under speech.
