import subprocess

src1 = r"C:\Users\lion_\OneDrive\Hermes\Agents\planning\sonic-studio\music-test-2026-07-29\C01-full-album-brief-short.mp3"
src2 = r"C:\Users\lion_\OneDrive\Hermes\Agents\planning\sonic-studio\music-test-2026-07-29\G02-pop-punk-grunge.mp3"
dst = r"C:\Users\lion_\OneDrive\Hermes\Agents\planning\sonic-studio\music-test-2026-07-29\test-crossfade.mp3"

filter_complex = (
    "[0:a]atrim=0:30,asetpts=PTS-STARTPTS[first]; "
    "[1:a]atrim=0:30,asetpts=PTS-STARTPTS[second]; "
    "[first][second]acrossfade=d=2:c1=tri:c2=tri[out]"
)

cmd = [
    "ffmpeg", "-hide_banner", "-nostats",
    "-y",
    "-i", src1,
    "-i", src2,
    "-filter_complex", filter_complex,
    "-map", "[out]",
    "-c:a", "libmp3lame",
    "-b:a", "192k",
    dst,
]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("rc:", proc.returncode)
print("stderr last 10:")
for line in proc.stderr.split('\n')[-10:]:
    print(' ', line)

import os
if os.path.exists(dst):
    print(f"\nfile size: {os.path.getsize(dst)} bytes")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1", dst],
        capture_output=True, text=True, timeout=30,
    )
    print(f"duration: {probe.stdout.strip()}")