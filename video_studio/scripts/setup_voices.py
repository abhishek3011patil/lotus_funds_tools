"""Install pinned public Kokoro model data; user text never leaves this machine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = ROOT / ".runtime" / "voices"
RELEASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1"
RELEASE_API = "https://api.github.com/repos/thewh1teagle/kokoro-onnx/releases/tags/model-files-v1.1"
DOWNLOAD_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
# Exact asset sizes and SHA-256 digests published in the upstream release API.
ASSETS = (
    {
        "name": "kokoro-v1.0.onnx",
        "bytes": 325505369,
        "sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    },
    {
        "name": "voices-v1.0.bin",
        "bytes": 28214398,
        "sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    },
)


class HTTPSRedirectsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if urllib.parse.urlsplit(new_url).scheme != "https":
            raise RuntimeError("The model download tried to redirect outside HTTPS.")
        return super().redirect_request(request, response, code, message, headers, new_url)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def valid_asset(path: Path, asset: dict) -> bool:
    return path.is_file() and path.stat().st_size == asset["bytes"] and digest(path) == asset["sha256"]


def check_models(directory: Path = VOICE_DIR) -> list[str]:
    """Return missing or invalid filenames without fetching or changing anything."""
    return [asset["name"] for asset in ASSETS if not valid_asset(directory / asset["name"], asset)]


def download_asset(asset: dict, directory: Path) -> None:
    target = directory / asset["name"]
    if valid_asset(target, asset):
        print(f"Verified existing {asset['name']}", flush=True)
        return
    opener = urllib.request.build_opener(HTTPSRedirectsOnly())
    for attempt in range(1, 4):
        partial = None
        try:
            print(f"Downloading {asset['name']} ({asset['bytes'] / 1024**2:.1f} MiB)...", flush=True)
            request = urllib.request.Request(
                DOWNLOAD_BASE + asset["name"],
                headers={"User-Agent": "Tarkash-Video-Studio-Installer/1.0", "Accept-Encoding": "identity"},
            )
            with opener.open(request, timeout=90) as response:
                declared_size = response.headers.get("Content-Length")
                if declared_size and int(declared_size) != asset["bytes"]:
                    raise RuntimeError(f"Unexpected download size for {asset['name']}.")
                with tempfile.NamedTemporaryFile(prefix=asset["name"] + ".", suffix=".part", dir=directory, delete=False) as output:
                    partial = Path(output.name)
                    checksum = hashlib.sha256()
                    received = 0
                    reported = -1
                    while block := response.read(1024 * 1024):
                        received += len(block)
                        if received > asset["bytes"]:
                            raise RuntimeError("The model download exceeded its pinned size.")
                        output.write(block)
                        checksum.update(block)
                        progress = min(100, (received * 100 // asset["bytes"] // 10) * 10)
                        if progress != reported:
                            print(f"  {progress}%", flush=True)
                            reported = progress
                    output.flush()
                    os.fsync(output.fileno())
            if received != asset["bytes"] or checksum.hexdigest() != asset["sha256"]:
                raise RuntimeError(f"Checksum verification failed for {asset['name']}; downloaded data was not activated.")
            os.replace(partial, target)
            partial = None
            print(f"Verified and installed {asset['name']}", flush=True)
            return
        except Exception as error:
            if attempt == 3:
                raise RuntimeError(f"Could not install {asset['name']}: {error}") from error
            print(f"Download failed: {error}. Retrying ({attempt}/3)...", flush=True)
            time.sleep(2 * attempt)
        finally:
            if partial is not None:
                partial.unlink(missing_ok=True)


def install_models() -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    for asset in ASSETS:
        download_asset(asset, VOICE_DIR)
    invalid = check_models()
    if invalid:
        raise RuntimeError("Voice pack is incomplete: " + ", ".join(invalid))
    provenance = {"model": "Kokoro v1.0 (full precision)", "release": RELEASE_URL, "releaseApi": RELEASE_API, "assets": ASSETS}
    temporary = VOICE_DIR / "model-manifest.json.part"
    temporary.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, VOICE_DIR / "model-manifest.json")
    print(f"Local voice pack ready in {time.perf_counter() - started:.1f}s: {VOICE_DIR}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify local file sizes and SHA-256 digests without network access.")
    args = parser.parse_args()
    try:
        if args.check:
            invalid = check_models()
            if invalid:
                raise RuntimeError("Missing or invalid voice data: " + ", ".join(invalid))
            print("Local Kokoro voice pack checksums passed.")
        else:
            install_models()
        return 0
    except Exception as error:
        print(f"Voice setup failed: {error}", file=sys.stderr)
        print("Run Install.cmd again to retry. Installed Windows voices remain available in the app.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
