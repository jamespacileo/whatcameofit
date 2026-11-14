"""Write a quiet background track for a video, made from nothing but arithmetic.

The track is synthesised here, note by note, so there is no recording, sample or
library behind it and no licence to check: it belongs to the project. The same
command always writes the same file.

It is a slow pad under sparse soft notes, four chords of eight seconds each, as long
as the video's narration (read from timing.json), with a fade at each end.

Run from video/:
  uv run --with numpy python3 scripts/music.py videos/what-came-of-it-explainer
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 48000
BAR = 8.0  # seconds a chord is held
# Cmaj9, Am9, Fmaj9, G6/9: no leading tone pulls anywhere, so it never sounds like an ending.
CHORDS = [
    [48, 55, 64, 71, 74],
    [45, 52, 60, 67, 71],
    [41, 48, 57, 64, 67],
    [43, 50, 59, 64, 69],
]
# Which chord tone each soft note plays, and on which half-second of the bar. Fixed, not random.
NOTES = [(0, 2), (3, 3), (6, 4), (9, 3), (12, 1), (14, 2)]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def pad(midi: int, seconds: float) -> np.ndarray:
    """One held note: a few quiet harmonics, slightly detuned, swelling in and out."""
    t = np.arange(int(seconds * RATE)) / RATE
    tone = np.zeros_like(t)
    for detune in (-0.04, 0.04):
        for harmonic, level in ((1, 1.0), (2, 0.22), (3, 0.07)):
            tone += level * np.sin(2 * np.pi * hz(midi + detune) * harmonic * t)
    swell = np.clip(t / 3.0, 0, 1) * np.clip((seconds - t) / 3.0, 0, 1)
    return tone * np.sin(swell * np.pi / 2) ** 2


def note(midi: int, seconds: float = 5.0) -> np.ndarray:
    """One soft struck note: a sine that starts gently and dies away."""
    t = np.arange(int(seconds * RATE)) / RATE
    tone = np.sin(2 * np.pi * hz(midi) * t) + 0.18 * np.sin(2 * np.pi * hz(midi) * 2 * t)
    return tone * np.clip(t / 0.012, 0, 1) * np.exp(-t * 1.5)


def add(track: np.ndarray, sound: np.ndarray, start: float, level: float) -> None:
    begin = int(start * RATE)
    end = min(begin + len(sound), len(track))
    if end > begin:
        track[begin:end] += level * sound[: end - begin]


def echo(track: np.ndarray, delay: float, feedback: float) -> np.ndarray:
    """A plain repeating echo, enough to give the notes some room."""
    out = track.copy()
    step = int(delay * RATE)
    for start in range(step, len(out), step):
        end = min(start + step, len(out))
        out[start:end] += feedback * out[start - step : start - step + (end - start)]
    return out


def main(folder: Path) -> None:
    length = json.loads((folder / "timing.json").read_text())["total_duration"]
    samples = int(length * RATE)
    left = np.zeros(samples)
    right = np.zeros(samples)

    for bar in range(int(length // BAR) + 1):
        chord = CHORDS[bar % len(CHORDS)]
        start = bar * BAR
        for index, midi in enumerate(chord):
            # The pad overlaps the next chord by its swell, so chords cross-fade.
            sound = pad(midi, BAR + 3.0)
            lean = 0.5 + 0.3 * (index / (len(chord) - 1) - 0.5)
            add(left, sound, start, 0.10 * (1 - lean))
            add(right, sound, start, 0.10 * lean)
        for number, (half, tone) in enumerate(NOTES):
            sound = note(chord[tone] + 12)
            lean = 0.35 if number % 2 else 0.65
            add(left, sound, start + half / 2, 0.16 * (1 - lean))
            add(right, sound, start + half / 2, 0.16 * lean)

    left = echo(left, 0.37, 0.32)
    right = echo(right, 0.43, 0.32)
    stereo = np.stack([left, right], axis=1)

    t = np.arange(samples) / RATE
    stereo *= (np.clip(t / 2.0, 0, 1) * np.clip((length - t) / 4.0, 0, 1))[:, None]
    stereo *= 10 ** (-6 / 20) / np.abs(stereo).max()  # peak at -6 dB

    with wave.open(str(folder / "bgm.wav"), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((stereo * 32767).astype("<i2").tobytes())
    print(f"bgm.wav  {length:.1f}s  peak -6 dB")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
