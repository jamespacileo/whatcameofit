"""Narrate a video's podcast.txt in English with Edge TTS.

Writes, into the video's folder:
  podcast_audio.wav   the narration, 48 kHz mono
  timing.json         section times (the shape the Remotion compositions read)
  captions.json       caption cues and per-word times
  podcast_audio.srt   the same cues, for upload beside the video

Each [SECTION:name] is spoken on its own, so its start is exact, with a short
pause after it. `{spoken|shown}` in the script says one thing and captions another:
`{what came of it dot com|whatcameofit.com}`.

Run from video/:
  uv run --with edge-tts python3 scripts/narrate.py videos/what-came-of-it-explainer
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

VOICE = os.environ.get("EDGE_TTS_VOICE", "en-GB-RyanNeural")
RATE = os.environ.get("TTS_RATE", "+0%")
FPS = 30
LEAD = 0.35  # silence before the first word of the video
GAP = 0.55  # silence between sections
TAIL = 1.6  # silence after the last word, for the closing card
CUE_CHARS = 40  # a caption breaks at punctuation, or once it is this long

SECTION = re.compile(r"^\[SECTION:([a-z0-9_]+)\]\s*$")
PAIR = re.compile(r"\{([^|{}]+)\|([^|{}]+)\}")


def read_sections(path: Path) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        found = SECTION.match(line.strip())
        if found:
            sections.append((found.group(1), []))
        elif line.strip() and not line.startswith("#") and sections:
            sections[-1][1].append(line.strip())
    return [(name, " ".join(lines)) for name, lines in sections]


def spoken(text: str) -> str:
    return PAIR.sub(lambda m: m.group(1), text)


def shown_tokens(text: str) -> list[tuple[str, int]]:
    """Caption tokens, each with the number of spoken words it stands for."""
    tokens: list[tuple[str, int]] = []
    position = 0
    for found in PAIR.finditer(text):
        tokens += [(word, 1) for word in text[position : found.start()].split()]
        tokens.append((found.group(2), len(found.group(1).split())))
        position = found.end()
    tokens += [(word, 1) for word in text[position:].split()]
    # Punctuation written after a pair belongs to the pair's token.
    merged: list[tuple[str, int]] = []
    for word, count in tokens:
        if merged and re.fullmatch(r"[.,:;?!]+", word):
            merged[-1] = (merged[-1][0] + word, merged[-1][1])
        else:
            merged.append((word, count))
    return merged


def norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


async def synthesize(text: str, mp3: Path) -> list[dict]:
    speech = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    words: list[dict] = []
    with mp3.open("wb") as out:
        async for chunk in speech.stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append(
                    {"text": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7}
                )
    return words


def align(script_words: list[str], heard: list[dict]) -> list[dict]:
    """Give each word of the script the time of the word(s) the voice reported."""
    # The voice may report "Phase 1" as one word or "2021" as two, so the two lists are
    # matched letter by letter: each letter carries the time of the word it was heard in.
    letters = [(char, item) for item in heard for char in norm(item["text"])]
    wanted = "".join(norm(word) for word in script_words)
    if "".join(char for char, _ in letters) != wanted:
        raise SystemExit(
            f"The voice reported different words from the script:\n  {wanted}\n  {''.join(c for c, _ in letters)}"
        )
    timed: list[dict] = []
    position = 0
    for word in script_words:
        size = len(norm(word))
        if not size:
            continue
        span = letters[position : position + size]
        position += size
        timed.append({"text": word, "start": span[0][1]["start"], "end": span[-1][1]["end"]})
    return timed


def cues_for(tokens: list[tuple[str, int]], timed: list[dict]) -> list[dict]:
    # Each token with its own times.
    items: list[dict] = []
    position = 0
    for word, count in tokens:
        span = timed[position : position + count]
        position += count
        items.append({"text": word, "start": span[0]["start"], "end": span[-1]["end"]})

    def length(group: list[dict]) -> int:
        return len(" ".join(item["text"] for item in group))

    # Clauses end at punctuation; a short one ending in a comma joins the next.
    clauses: list[list[dict]] = []
    current: list[dict] = []
    for item in items:
        current.append(item)
        mark = item["text"][-1]
        if mark in ".?!:" or (mark in ",;" and length(current) >= 18):
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)

    # A clause too long for one caption is cut into even parts, never leaving one word alone.
    groups: list[list[dict]] = []
    for clause in clauses:
        parts = -(-length(clause) // (CUE_CHARS + 6))
        if parts <= 1:
            groups.append(clause)
            continue
        target = length(clause) / parts
        part: list[dict] = []
        for index, item in enumerate(clause):
            part.append(item)
            left = len(clause) - index - 1
            if length(part) >= target and left >= 2 and len(groups_in_clause := part) >= 2:
                groups.append(groups_in_clause)
                part = []
        if part:
            groups.append(part)

    cues: list[dict] = []
    for group in groups:
        start = max(group[0]["start"], cues[-1]["end"] if cues else 0.0)
        cues.append(
            {"text": " ".join(item["text"] for item in group), "start": start, "end": max(group[-1]["end"], start + 0.3)}
        )
    return cues


def stamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    return f"{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02},{millis % 1000:03}"


def run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True)


async def main(folder: Path) -> None:
    sections = read_sections(folder / "podcast.txt")
    if not sections:
        raise SystemExit("No [SECTION:name] markers in podcast.txt")

    timing_sections: list[dict] = []
    all_cues: list[dict] = []
    all_words: list[dict] = []
    clock = LEAD

    with tempfile.TemporaryDirectory() as scratch:
        parts: list[Path] = []
        for number, (name, text) in enumerate(sections):
            mp3 = Path(scratch) / f"{number}.mp3"
            heard = await synthesize(spoken(text), mp3)
            timed = align(spoken(text).split(), heard)
            last = number == len(sections) - 1
            length = timed[-1]["end"] + (TAIL if last else GAP)
            lead = LEAD if number == 0 else 0.0

            # One part per section: its speech, cut after the last word, then the pause.
            part = Path(scratch) / f"{number}.wav"
            run(
                "ffmpeg", "-y", "-v", "error", "-i", str(mp3),
                "-af", f"adelay={round(lead * 1000)},apad,atrim=0:{lead + length:.3f}",
                "-ar", "48000", "-ac", "1", str(part),
            )  # fmt: skip
            parts.append(part)

            begin = 0.0 if number == 0 else clock
            for word in timed:
                all_words.append(
                    {"text": word["text"], "start": round(clock + word["start"], 3), "end": round(clock + word["end"], 3)}
                )
            shifted = [{**w, "start": clock + w["start"], "end": clock + w["end"]} for w in timed]
            for cue in cues_for(shown_tokens(text), shifted):
                all_cues.append(
                    {"text": cue["text"], "start": round(cue["start"], 3), "end": round(cue["end"], 3), "section": name}
                )
            clock += length
            timing_sections.append(
                {
                    "name": name,
                    "label": name,
                    "start_time": round(begin, 3),
                    "end_time": round(clock, 3),
                    "duration": round(clock - begin, 3),
                    "start_frame": round(begin * FPS),
                    "duration_frames": round(clock * FPS) - round(begin * FPS),
                    "is_silent": False,
                }
            )

        listing = Path(scratch) / "parts.txt"
        listing.write_text("".join(f"file '{part}'\n" for part in parts))
        run(
            "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c:a", "pcm_s16le", str(folder / "podcast_audio.wav"),
        )  # fmt: skip

    timing = {
        "total_duration": round(clock, 3),
        "fps": FPS,
        "total_frames": round(clock * FPS),
        "speech_rate": RATE,
        "voice": VOICE,
        "sections": timing_sections,
    }
    (folder / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
    (folder / "captions.json").write_text(
        json.dumps({"cues": all_cues, "words": all_words}, indent=1) + "\n"
    )
    (folder / "podcast_audio.srt").write_text(
        "".join(
            f"{n}\n{stamp(cue['start'])} --> {stamp(cue['end'])}\n{cue['text']}\n\n"
            for n, cue in enumerate(all_cues, 1)
        ),
        encoding="utf-8",
    )
    for section in timing_sections:
        print(f"{section['name']:>10}  {section['start_time']:6.2f}s  {section['duration']:5.2f}s")
    print(f"     total  {clock:.2f}s  {timing['total_frames']} frames  {len(all_cues)} cues")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
