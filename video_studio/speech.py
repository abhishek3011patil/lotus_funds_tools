"""Local Windows and AI narration; input text is always data."""
import hashlib
import json
import os
import re
import subprocess
import threading
import uuid
import wave
from pathlib import Path
import natural_speech

ROOT = Path(__file__).resolve().parent
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
_synthesis_lock = threading.RLock()
PREVIEW_TEXT = ('Good morning. Here is your market briefing. Nifty is trading near twenty-three thousand, '
                'while Bank Nifty and Sensex remain in focus. Watch the key levels, manage your risk, '
                'and wait for a clear trend before taking action.')

def run_ps(args, timeout=180):
    if os.name != 'nt':
        raise RuntimeError('Offline narration requires Windows. Turn narration off on other platforms.')
    proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts' / 'speech.ps1'), *args], capture_output=True, timeout=timeout, creationflags=FLAGS)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode('utf-8', errors='replace')[-1500:] or 'Windows voice generation failed.')
    return proc.stdout.decode('utf-8-sig', errors='replace').strip()

def voices():
    try:
        result = json.loads(run_ps(['-ListVoices'], 20))
        return result if isinstance(result, list) else [result]
    except Exception:
        return []


def voice_catalog(windows_voices=None):
    installed = voices() if windows_voices is None else windows_voices
    return natural_speech.catalog() + [dict(v, engine='windows', available=True) for v in installed]


def voice_engine(voice):
    return 'kokoro' if voice.startswith('kokoro:') else 'windows'


def require_voice(voice, windows_voices=None):
    if voice_engine(voice) == 'kokoro':
        if voice.removeprefix('kokoro:') not in natural_speech.VOICE_NAMES:
            raise ValueError('Choose one of the listed AI voices.')
        if not natural_speech.status()['available']:
            raise ValueError(natural_speech.status()['message'])
        if voice.removeprefix('kokoro:') in natural_speech.EXTRA_VOICES and not natural_speech.INDIAN_PERSONAS.is_file():
            raise ValueError('Indian English voices are missing. Reinstall the studio voice pack.')
    else:
        installed = voices() if windows_voices is None else windows_voices
        if not installed:
            raise ValueError('No Windows voices are installed. Choose an AI voice or turn narration off.')
        if voice and voice not in {v['id'] for v in installed}:
            raise ValueError('That Windows voice is not available on this computer. Choose a listed voice.')

def spoken_text(section):
    if section.get('narration', '').strip():
        return section['narration'].strip()
    text = section.get('title', '') + '. ' + section.get('body', '')
    if section.get('rows'):
        for row in section['rows']:
            text += f"\n{row.get('metric', '')}. Nifty {row.get('nifty', '')}. Sensex {row.get('sensex', '')}. Bank Nifty {row.get('bankNifty', '')}."
    text = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]', '', text)
    text = re.sub(r'[#*•]', '', text)
    text = text.replace('₹', ' rupees ').replace('&', ' and ')
    # The voice engine collapses newlines. Give headings, table rows, and
    # bullet-style lines real sentence boundaries while keeping slide text as-is.
    phrases = []
    for line in text.splitlines():
        for part in line.split('|'):
            phrase = re.sub(r'\s+', ' ', part).strip()
            if not phrase:
                continue
            if phrase[-1] not in '.!?':
                phrase += '.'
            phrases.append(phrase)
    return ' '.join(phrases)

def synthesize(text, settings, cache):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Enter some text for the narrator to read.')
    cache.mkdir(parents=True, exist_ok=True)
    voice = settings.get('voice', '')
    rate = max(-5, min(5, int(settings.get('speechRate', 0))))
    engine = voice_engine(voice)
    version = natural_speech.CACHE_VERSION if engine == 'kokoro' else 'windows-v1'
    key = hashlib.sha256(json.dumps([version, text, voice, rate], ensure_ascii=False).encode()).hexdigest()
    out = cache / (key + '.wav')
    with _synthesis_lock:
        if not out.exists():
            temporary = cache / (key + '.' + uuid.uuid4().hex + '.tmp.wav')
            request = None
            try:
                if engine == 'kokoro':
                    natural_speech.create_wav(text, voice, rate, temporary)
                else:
                    request = temporary.with_suffix('.json')
                    request.write_text(json.dumps({'text': text, 'voice': voice, 'rate': rate,
                                                  'output': str(temporary)}, ensure_ascii=False), encoding='utf-8')
                    run_ps(['-RequestPath', str(request)])
                with wave.open(str(temporary)) as stream:
                    if stream.getnframes() <= 0:
                        raise RuntimeError('The selected voice produced empty audio.')
                temporary.replace(out)
            finally:
                temporary.unlink(missing_ok=True)
                if request is not None:
                    request.unlink(missing_ok=True)
        with wave.open(str(out)) as w:
            duration = w.getnframes() / w.getframerate()
    return out, duration
