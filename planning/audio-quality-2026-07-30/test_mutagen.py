"""Test ID3v2.4 metadata embedding via mutagen.

Recipe to embed:
- artist (TPE1)
- album (TALB)
- title (TIT2)
- track number (TRCK)
- year (TDRC, ID3v2.4)
- genre (TCON)
- lyrics (USLT, unsynced)
- cover art (APIC)
"""

import sys
from mutagen.id3 import ID3, ID3NoHeaderError, TPE1, TALB, TIT2, TRCK, TCON, TDRC, USLT, APIC, ID3FileType

src = r"C:\Users\lion_\OneDrive\Hermes\Agents\planning\album-studio\music-test-2026-07-29\C01-full-album-brief-short.mp3"
dst = r"C:\Users\lion_\OneDrive\Hermes\Agents\planning\album-studio\audio-quality-2026-07-30\C01-with-id3.mp3"

import shutil
shutil.copy(src, dst)

try:
    audio = ID3(dst)
except ID3NoHeaderError:
    audio = ID3FileType(dst)
    audio.add_tags()

audio.add(TPE1(encoding=3, text="Maren Sol"))
audio.add(TALB(encoding=3, text="Half-Light Hours"))
audio.add(TIT2(encoding=3, text="Sundown on Bleecker"))
audio.add(TRCK(encoding=3, text="01/10"))
audio.add(TCON(encoding=3, text="Indie Rock"))
audio.add(TDRC(encoding=3, text="2026"))
audio.add(USLT(encoding=3, lang="eng", desc="", text="[Verse 1]\nBurned out on the weekday news\nStuck inside a world of blues\n..."))
audio.save()

# Read back
audio2 = ID3(dst)
for key in audio2.keys():
    print(f"  {key}: {audio2[key]}")

print()
print("file size:", __import__("os").path.getsize(dst), "bytes")