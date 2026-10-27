"""Local Kokoro narration. Model data and text stay on this computer."""
from importlib.util import find_spec
import importlib
from pathlib import Path
import os
import threading
import wave

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / '.runtime' / 'voices'
MODEL = MODEL_DIR / 'kokoro-v1.0.onnx'
VOICE_DATA = MODEL_DIR / 'voices-v1.0.bin'
INDIAN_PERSONAS = ROOT / 'assets' / 'voices' / 'indian-english-personas.npz'
MODEL_SIZE = 325505369
VOICE_DATA_SIZE = 28214398
CACHE_VERSION = 'kokoro-onnx-0.6.1-model-v1.0-fp32-pauses-v3'
VOICE_NAMES = {
    'af_heart': 'Heart · US English · female',
    'af_bella': 'Bella · US English · female',
    'am_michael': 'Michael · US English · male',
    'am_fenrir': 'Fenrir · US English · male',
    'bf_emma': 'Emma · British English · female',
    'bm_george': 'George · British English · male',
    'hf_alpha': 'Alpha · Indian female',
    'en_ananya': 'Ananya · Indian English · female',
    'en_divya': 'Divya · Indian English · female',
    'en_priya': 'Priya · Indian English · female',
}
EXTRA_VOICES = frozenset(('en_ananya', 'en_divya', 'en_priya'))
_model = None
_personas = None
_lock = threading.RLock()


def status():
    ready = (MODEL.is_file() and MODEL.stat().st_size == MODEL_SIZE and
             VOICE_DATA.is_file() and VOICE_DATA.stat().st_size == VOICE_DATA_SIZE and
             find_spec('kokoro_onnx') is not None and find_spec('onnxruntime') is not None)
    if ready:
        # Detect missing native runtime DLLs before offering an unusable voice.
        # Python caches imports; this does not load the large speech model.
        try:
            importlib.import_module('onnxruntime')
            importlib.import_module('kokoro_onnx')
        except (ImportError, OSError):
            ready = False
    return {'available': ready, 'message': (
        'Ten free AI voices, including four Indian female choices. Works offline; no account or subscription needed.' if ready else
        'Run Install.cmd to add the free AI voice pack, then reopen the studio. First setup needs internet.')}


def catalog():
    available = status()['available']
    return [{'id': 'kokoro:' + key, 'name': name, 'engine': 'kokoro',
             'available': available and (key not in EXTRA_VOICES or INDIAN_PERSONAS.is_file())}
            for key, name in VOICE_NAMES.items()]


def create_wav(text, voice_id, rate, destination):
    """Write a complete 24 kHz mono PCM file using a bounded CPU session."""
    global _model, _personas
    voice = voice_id.removeprefix('kokoro:')
    if voice not in VOICE_NAMES:
        raise ValueError('Choose one of the listed AI voices.')
    if not status()['available']:
        raise RuntimeError(status()['message'])
    import numpy as np
    import onnxruntime as ort
    from kokoro_onnx import Kokoro

    with _lock:
        if _model is None:
            options = ort.SessionOptions()
            options.intra_op_num_threads = min(8, max(1, (os.cpu_count() or 2) // 2))
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(MODEL), sess_options=options,
                                          providers=['CPUExecutionProvider'])
            _model = Kokoro.from_session(session, str(VOICE_DATA))
        if voice in EXTRA_VOICES:
            if _personas is None:
                if not INDIAN_PERSONAS.is_file():
                    raise RuntimeError('Indian English voices are missing. Reinstall the studio voice pack.')
                with np.load(INDIAN_PERSONAS, allow_pickle=False) as archive:
                    _personas = {name: np.asarray(archive[name], dtype=np.float32)
                                 for name in EXTRA_VOICES}
                if any(value.shape != (510, 1, 256) or not np.isfinite(value).all()
                       for value in _personas.values()):
                    _personas = None
                    raise RuntimeError('The Indian English voice pack is invalid. Reinstall the studio.')
            selected_voice = _personas[voice]
        else:
            selected_voice = voice
        speed = round(1 + max(-5, min(5, rate)) * .06, 2)
        samples, sample_rate = _model.create(text, voice=selected_voice, speed=speed,
                                            lang='en-gb' if voice.startswith('b') else 'en-us',
                                            sentence_pause=0.55, clause_pause=0.22)
        samples = np.asarray(samples).reshape(-1)
        if not len(samples) or not np.isfinite(samples).all():
            raise RuntimeError('The voice could not produce valid audio. Try another voice or shorten the script.')
        pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2')
        with wave.open(str(destination), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(int(sample_rate))
            stream.writeframes(pcm.tobytes())
