"""Fail setup if the private runtime cannot render or encode video."""

import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright


def verify_voices():
    try:
        import numpy as np
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
    except (ImportError, OSError) as error:
        raise RuntimeError(
            'Local neural speech dependencies could not load. Windows needs the Microsoft '
            'Visual C++ 2015-2022 x64 runtime: https://aka.ms/vs/17/release/vc_redist.x64.exe. '
            'Installed Windows voices remain available. Details: ' + str(error)
        ) from error
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.setup_voices import VOICE_DIR, check_models
    invalid = check_models()
    if invalid:
        raise RuntimeError('Local voice pack needs repair: ' + ', '.join(invalid))
    started = time.perf_counter()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(VOICE_DIR / 'kokoro-v1.0.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    kokoro = Kokoro.from_session(session, str(VOICE_DIR / 'voices-v1.0.bin'))
    samples, sample_rate = kokoro.create('Your local video studio is ready.', voice='af_heart', speed=1.0, lang='en-us')
    if sample_rate != 24000 or len(samples) < sample_rate // 2 or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.001:
        raise RuntimeError('Local speech generation did not produce valid audible samples.')
    print(f'Kokoro local speech verified: {len(samples) / sample_rate:.2f}s audio in {time.perf_counter() - started:.2f}s; {len(kokoro.get_voices())} voices.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-voices', action='store_true', help='Fail if local neural speech models or synthesis are unavailable.')
    args = parser.parse_args()
    for name in ("fastapi", "uvicorn", "multipart", "PIL", "playwright"):
        importlib.import_module(name)
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-version"],
        capture_output=True,
        text=True,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print(result.stdout.splitlines()[0])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 180})
        page.set_content("<h1>Video Studio is ready</h1>")
        assert page.locator("h1").inner_text() == "Video Studio is ready"
        assert len(page.screenshot()) > 100
        print("Chromium rendering verified:", browser.version)
        browser.close()
    if args.require_voices:
        verify_voices()
    print("All runtime checks passed.")


if __name__ == "__main__":
    main()
