# Third-party notices for local neural narration

Tarkash Video Studio uses the following third-party software and model data for local Kokoro narration. The large base model and dependency wheels are downloaded during installation. The installation ZIP contains this notice, the full license texts listed below, the downloader, and three small Indian English persona voicepacks.

The ending slide uses the [Bootstrap Icons Twitter bird SVG](https://github.com/twbs/icons/blob/main/icons/twitter.svg), licensed under MIT. Its copyright and license text are included at [installer/licenses/bootstrap-icons-MIT.txt](installer/licenses/bootstrap-icons-MIT.txt).

| Component | Installed version | Upstream / source | License text included here |
| --- | --- | --- | --- |
| Kokoro-82M model and voice embeddings | v1.0, full-precision ONNX export | [Original model and license metadata](https://huggingface.co/hexgrad/Kokoro-82M), [ONNX export release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1) | Apache License 2.0: [full text](installer/licenses/kokoro-model-Apache-2.0.txt) |
| Goonj Indian English persona voicepacks (Ananya, Divya, Priya) | Three voicepacks from `BH-Builds/goonj-1-82M`, stored as NumPy arrays without executable pickle data | [Model card and license metadata](https://huggingface.co/BH-Builds/goonj-1-82M) | Apache License 2.0: [full text](installer/licenses/kokoro-model-Apache-2.0.txt) |
| kokoro-onnx Python wrapper | 0.6.1 | [Project source](https://github.com/thewh1teagle/kokoro-onnx), [published package](https://pypi.org/project/kokoro-onnx/0.6.1/) | MIT: [full text and copyright](installer/licenses/kokoro-onnx-MIT.txt) |
| espeakng-loader Python wrapper | 0.2.4 | [Project source](https://github.com/thewh1teagle/espeakng-loader), [published package](https://pypi.org/project/espeakng-loader/0.2.4/) | MIT for the loader: [full text and copyright](installer/licenses/espeakng-loader-MIT.txt) |
| eSpeak NG library and language data, included by espeakng-loader | 1.52.0 | [Versioned upstream source](https://github.com/espeak-ng/espeak-ng/tree/1.52.0), [source archive](https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz) | GNU GPL version 3 or later: [full text](installer/licenses/espeak-ng-GPL-3.0.txt) |
| phonemizer | 3.4.0 | [Project source](https://github.com/bootphon/phonemizer), [published package and source download](https://pypi.org/project/phonemizer/3.4.0/#files) | GNU GPL version 3 or later: [full text](installer/licenses/phonemizer-GPL-3.0.txt) |

The loader's MIT license does **not** replace the GPL license of the eSpeak NG library/data it includes. Both eSpeak NG and phonemizer are GPL-licensed components; the speech stack must not be represented as entirely permissively licensed. Preserve applicable copyright and license notices and comply with the relevant source-availability and other terms when redistributing or embedding these components, including a future Tarkash website or desktop product. Upstream source and complete license texts are provided above; all third-party components are used without source modifications by this installer.

The eSpeak NG source version is recorded by the upstream loader build configuration; the DLL supplied by the installed 0.2.4 Windows wheel was also checked through `espeak_Info` and reported 1.52.0. Its upstream source tag resolves to commit `4870adfa25b1a32b4361592f1be8a40337c58d6c`.

## Model downloads and integrity

The model is named v1.0 even though its upstream export release tag is `model-files-v1.1`. The exact files below are downloaded over HTTPS from that release and accepted only after byte-size and SHA-256 verification. Downloads are first written to temporary files and activated atomically after validation. Interrupted or invalid downloads do not replace an already installed model.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `kokoro-v1.0.onnx` | 325,505,369 | `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a` |
| `voices-v1.0.bin` | 28,214,398 | `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d` |

The pinned values come from the [upstream GitHub release API](https://api.github.com/repos/thewh1teagle/kokoro-onnx/releases/tags/model-files-v1.1). Files are stored in `.runtime/voices` beside a provenance manifest. The installer fetches only public package/model data; it does not upload user text, scripts, voice recordings, projects, or generated audio. Kokoro synthesis runs on this computer's CPU.

The three Goonj voicepacks came from the publisher's `voices/en_ananya.pt`, `voices/en_divya.pt`, and `voices/en_priya.pt`. Their tensor data was repackaged without the PyTorch pickle wrapper into `assets/voices/indian-english-personas.npz` (SHA-256 `dbfeb932b0ca101efddb4a962a35fd407e8309155af6a971e4f45aeb27c5c8c3`). The original files' SHA-256 values, respectively, are `8c31ff3422c8c49bdabd0f2b4dbf88eb78bf54e91ac537c34de749893040c740`, `bcb297521e1d3b350b731a9370867730bf90af9e6ae3b07042a848c727910502`, and `4e24424f158d129f2e91a998973980a32921cbaacc5459084c81732852a56d5e`. These Goonj voicepacks are used with the base Kokoro ONNX model, rather than the Goonj fine-tuned weights; listen to a sample before publishing because this experimental pairing may sound different from the publisher's demos.

## Other runtime dependencies

ONNX Runtime, NumPy, and the supporting Python packages keep their upstream license notices in the installed distributions under `.runtime/python/Lib/site-packages`. The exact speech dependency versions are pinned in `requirements.txt`. Existing video/UI dependencies retain their own upstream licenses as well. This notice does not remove, replace, or modify any upstream license terms or warranties.

Windows builds of ONNX Runtime require the [Microsoft Visual C++ runtime](https://onnxruntime.ai/docs/install/#requirements). If it is missing, setup reports the failure and provides the official Microsoft download link. The installer does not silently change system-wide Microsoft runtimes or require administrator access for its own private Python, model, browser, and package installation.
