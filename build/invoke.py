"""build/invoke.py - mmx dispatcher (Day 6).

Per plan section Day 6: dispatcher (action to mmx API call).

Maps pipeline layer mmx_action to a concrete mmx CLI invocation.
Returns an InvokeResult with stdout, stderr, exit_code, output_path.

Per user memory (Windows mmx gotchas, verified 2026-07-29):
  - Use raw string .cmd path: r"C:\\Users\\lion_\\...\\mmx.cmd"
  - Pass --lyrics "." to bypass broken --instrumental/--lyrics-optimizer
  - Real newline byte 0x0a in lyrics causes CreateProcess to split
    command line; CLI silently ignores --out. Escape literal newline
    to the two-char backslash-n sequence (mmx CLI decodes it back).
  - mmx CLI returns rc=6 on transport failure - retry once after 30s.

Per v3.4 section A.3, mmx_action values are stored in pipeline-deps.json
under each layer mmx_action field. Valid actions:
  - None             - no-op (manual-only layer)
  - "music.generate" - mmx music generate (with --lyrics ".")
  - "image.generate" - mmx image generate
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_log = logging.getLogger("sonic_sounds.build.invoke")

# Per memory: must be the raw .cmd path so CreateProcess resolves it.
_DEFAULT_MMX_CMD = Path(
    r"C:\Users\lion_\AppData\Roaming\npm\mmx.cmd"
)

# Per memory: rc=6 = transport failure, retry after 30s.
_MMX_RETRY_RC = 6
_MMX_RETRY_DELAY_SEC = 30.0


@dataclass
class InvokeResult:
    """Outcome of a single mmx invocation."""
    action: str
    args: list
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    output_path: Optional[str] = None
    elapsed_sec: float = 0.0
    retried: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def _resolve_mmx_cmd() -> str:
    """Pick the mmx CLI path. Honours SONIC_SOUNDS_MMX_CMD env var."""
    override = os.environ.get("SONIC_SOUNDS_MMX_CMD")
    if override:
        return override
    return str(_DEFAULT_MMX_CMD)


def _escape_for_cmd(s) -> str:
    """Escape a value for the Windows cmd command line.

    Per Day 5 memory: real newline byte 0x0a in lyrics string causes
    CreateProcess to split the command line, which silently breaks
    --out. We replace any newline with the literal two-char backslash-n
    sequence. The mmx CLI receives the escaped form and decodes it
    back to a real newline.

    Also: backslashes and double quotes are escaped so the surrounding
    double quotes don't terminate prematurely.
    """
    if s is None:
        return ""
    s = str(s)
    BS = chr(92)       # backslash
    DQ = chr(34)       # double quote
    s = s.replace(BS, BS + BS)          # \\ -> \\
    s = s.replace(DQ, BS + DQ)          # " -> \"
    s = s.replace(chr(10), BS + "n")    # newline -> \n (two chars)
    s = s.replace(chr(13), BS + "r")    # CR -> \r
    return s


def invoke_music_generate(*,
                          output_dir: Path,
                          prompt: str = "",
                          duration_sec: int = 60,
                          lyrics=None,
                          instrumental: bool = True,
                          retry_on_transport_error: bool = True) -> InvokeResult:
    """Invoke mmx music generate and return the result.

    Per memory: pass --lyrics "." to bypass the broken
    --lyrics-optimizer/--instrumental flag detection. If lyrics is
    provided, escape newlines (Day 5 CRITICAL lesson).
    """
    mmx = _resolve_mmx_cmd()
    output_dir.mkdir(parents=True, exist_ok=True)

    lyrics_arg = _escape_for_cmd(lyrics) if lyrics else "."

    args = [
        mmx, "music", "generate",
        "--out", _escape_for_cmd(str(output_dir)),
        "--duration", str(duration_sec),
        "--lyrics", lyrics_arg,
        "--prompt", _escape_for_cmd(prompt) if prompt else "ambient album track",
    ]
    if instrumental:
        args.append("--instrumental")

    result = _run(args)
    result.output_path = _extract_output_path(result.stdout, output_dir)
    if not result.ok and result.exit_code == _MMX_RETRY_RC and retry_on_transport_error:
        _log.info(f"mmx returned rc={result.exit_code}, retrying after {_MMX_RETRY_DELAY_SEC}s")
        time.sleep(_MMX_RETRY_DELAY_SEC)
        result = _run(args)
        result.retried = True
        result.output_path = _extract_output_path(result.stdout, output_dir)
    return result


def invoke_image_generate(*,
                           output_dir: Path,
                           prompt: str,
                           size: str = "1024x1024",
                           retry_on_transport_error: bool = True) -> InvokeResult:
    """Invoke mmx image generate and return the result."""
    mmx = _resolve_mmx_cmd()
    output_dir.mkdir(parents=True, exist_ok=True)

    args = [
        mmx, "image", "generate",
        "--prompt", _escape_for_cmd(prompt),
        "--out", _escape_for_cmd(str(output_dir)),
        "--size", size,
    ]
    result = _run(args)
    result.output_path = _extract_output_path(result.stdout, output_dir)
    if not result.ok and result.exit_code == _MMX_RETRY_RC and retry_on_transport_error:
        _log.info(f"mmx returned rc={result.exit_code}, retrying after {_MMX_RETRY_DELAY_SEC}s")
        time.sleep(_MMX_RETRY_DELAY_SEC)
        result = _run(args)
        result.retried = True
        result.output_path = _extract_output_path(result.stdout, output_dir)
    return result


def invoke(*, action, album_id: str, layer_id: str,
           output_base: Path, **kwargs) -> InvokeResult:
    """Dispatch by action (the mmx_action value from pipeline-deps.json).

    For action=None, returns a no-op result (manual-only layers
    have no mmx_action and must be handled by the runner).
    """
    out_dir = Path(output_base) / album_id / layer_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if action is None:
        _log.info(f"layer {layer_id} has no mmx_action - no-op invoke")
        return InvokeResult(action="<none>", args=[], exit_code=0, stdout="",
                            output_path=str(out_dir / "MANUAL.md"))

    if action == "music.generate":
        return invoke_music_generate(
            output_dir=out_dir,
            prompt=kwargs.get("prompt", ""),
            duration_sec=kwargs.get("duration_sec", 60),
            lyrics=kwargs.get("lyrics"),
            instrumental=kwargs.get("instrumental", True),
        )
    if action == "image.generate":
        return invoke_image_generate(
            output_dir=out_dir,
            prompt=kwargs.get("prompt", ""),
            size=kwargs.get("size", "1024x1024"),
        )
    raise ValueError(f"unknown mmx_action: {action!r}")


def _run(args) -> InvokeResult:
    """Run mmx subprocess. Single source of subprocess-call truth."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=180,
        )
        elapsed = time.monotonic() - start
        return InvokeResult(
            action=" ".join(args[1:3]) if len(args) > 2 else "mmx",
            args=list(args),
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            elapsed_sec=elapsed,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - start
        _log.error(f"mmx invocation timed out after {elapsed:.1f}s")
        return InvokeResult(
            action="mmx",
            args=list(args),
            exit_code=124,
            stdout="",
            stderr=f"TIMEOUT after {elapsed:.1f}s: {e}",
            elapsed_sec=elapsed,
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        _log.error(f"mmx invocation failed: {e}")
        return InvokeResult(
            action="mmx",
            args=list(args),
            exit_code=1,
            stdout="",
            stderr=f"{type(e).__name__}: {e}",
            elapsed_sec=elapsed,
        )


def _extract_output_path(stdout: str, output_dir: Path):
    """Try to parse the actual output file path from mmx stdout.

    mmx writes the result path on its last stdout line. We fall back
    to the most recent file in output_dir if parsing fails.
    """
    candidates = []
    extensions = (".mp3", ".wav", ".jpg", ".jpeg", ".png", ".json")
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            tail = line.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39))
            if any(tail.lower().endswith(ext) for ext in extensions):
                candidates.append(Path(tail))
        elif line.startswith("/") or (len(line) > 2 and line[1] == ":"):
            if any(line.lower().endswith(ext) for ext in extensions):
                candidates.append(Path(line))
    if candidates:
        return str(candidates[-1])
    try:
        files = sorted(output_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            return str(files[0])
    except FileNotFoundError:
        pass
    return None
