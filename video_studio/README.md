# Tarkash Video Studio

A local Windows tool for preparing branded market update videos from one shared daily content set. Edit the content once, choose the brands to generate, and export individual MP4 videos. Text, emojis, logos, brand colors, contact details, and disclaimer text can be customized in the app.

For the complete step-by-step workflow, including voice pauses and every main studio feature, see [HOW-TO-USE.md](HOW-TO-USE.md).

## Install and open

1. Put the complete application folder in a permanent, writable location. If you received a ZIP, **extract it first**.
2. Double-click **Install.cmd**. Setup downloads a private Python runtime, the application dependencies, a Chromium rendering browser, the video encoder, and the free AI voice pack (about 354 MB for voice model data). The first run needs internet and can take several minutes.
3. The application opens in your browser. Use the **Tarkash Video Studio** desktop shortcut or **Launch.cmd** next time.

You do not need to install Python separately or run setup as administrator. Setup writes its runtime to `.runtime` inside this folder and creates a shortcut for the current Windows user. It does not change system Python, your PATH, or the machine's execution policy. Windows 10/11 on Intel/AMD 64-bit is supported; this installer has not been prepared for macOS, Linux, or Windows ARM.

Keep the folder in place after installing so the shortcut can find it. If you move it, run Install.cmd in the new location to recreate the shortcut. Launch.cmd also starts setup if the private runtime is missing.

## Working with videos

The daily content consists of the opening analysis, market trends, NIFTY / SENSEX / BANK NIFTY table, and two stock news sections. The shared content is reused across the selected brand outputs. Review brand colors, logos, contact details, and disclaimer wording before exporting.

1. In **Daily content**, update the date and each section. Paste emojis directly or use the emoji picker. Leave the optional voice script empty to narrate the displayed content, or enter different spoken wording. Choose a narrator and use **Listen to voice** to compare a short sample before exporting.
2. In **Brands & endings**, choose a brand or click **Add brand**. Upload its logo to select matching colors automatically; white, black and gray are ignored. You can refine the colors manually or press **Use logo colors** again. Edit the contact information and ending, then check the preview before exporting. A project can hold up to 40 brands.
3. In **Export studio**, select the brand versions, choose 720p or 1080p, and choose one narrator for every selected company. Click **Generate videos** and download the completed MP4 files from the results. Changes save automatically; **Save backup** downloads the project settings.

The starting project contains sample content transcribed from your supplied videos. Its editable project date is not a claim that the underlying market figures are current. Update the date, text, and table before preparing a new day's video.

**Lotus Insights** has a separate script because its source video differs from the shared Morning Action content. Edit it in the Insights content area, or enable its **Use shared daily content** option (`useSharedContent`) to use the common daily sections instead. The other brand versions reuse the shared content.

The source-video collection is reference material. Videos in nested exception folders are not batch targets. The app uses the prepared brand assets and templates; it does not rewrite or alter the original videos. Original source videos are not required by the distributable application.

The opening and closing pages use the approved HTML slide design. Their backgrounds reuse the clean market artwork from the supplied videos and stay still. The opening title and information cards slide into place in sequence; the closing information enters gently and then stays readable. The five shared content sections remain still slides; paragraphs are balanced vertically and the complete market table fills its page. Each brand's saved colors theme its pages. These animations differ from the exact Canva animations. The original source MP4 files are not required for exports or installation; the reusable artwork is included with the app.

Project edits are saved locally to `data/project.json`. Uploaded images stay in `assets/uploads`, and completed videos are written to `outputs`. Keep those folders when backing up your work. Exporting the project JSON preserves text and settings; copy its uploaded images as well when transferring a customized project to another computer.

Narration follows the editable text. Ten free **Natural voices** are included: Heart, Bella, Michael and Fenrir (US English), Emma and George (British English), and Alpha, Ananya, Divya and Priya (Indian female choices). Alpha is from Kokoro's Hindi voice set. Ananya, Divya and Priya use [Goonj Indian English persona voicepacks](https://huggingface.co/BH-Builds/goonj-1-82M) through the local Kokoro engine; this is an experimental pairing with the base model, so audition market names and figures before export. Beta is no longer offered. They need no account, subscription, API key or internet after setup. Windows voices remain available in a separate group. Choose a voice, press **Listen to voice**, then adjust speaking pace if needed. The sample is a fixed market briefing so voices are easy to compare; exports read your actual edition. The same text/voice/pace can reuse cached audio, and edited text creates new narration.

For clearer pauses, leave **Voice script** blank so headings, separators and lines become sentences automatically. If you enter a custom voice script, put a full stop or question mark at each intended sentence break; a line break alone may run together. The natural voices add a longer pause after sentence punctuation. Set **Speaking pace** to -1 or -2 if the voice still feels rushed. Previously exported MP4 files do not change; generate a new video to hear these changes.

These are alternative narrators, not a clone of the original video voice. Using the exact original AI narrator for new text requires identifying its source app and voice. English pronunciation varies by voice; listen to market names and figures before publishing. Rendering and voice generation speed depend on the computer. Third-party component licenses and source links are recorded in **THIRD_PARTY_NOTICES.md**.

The app uses a local service at `http://127.0.0.1:8765`. Keep the app running while exporting a video. Closing the browser does not stop the local service. Double-click **Stop.cmd** when exports are finished to stop an instance opened by the installed launcher; Launch.cmd starts it again. Stopping the app interrupts any unfinished exports.

The project contains a Python API and browser UI that can be integrated into the Tarkash website in a later project; no website deployment or online account system is included in this local installation.

## If setup or startup fails

- Keep an internet connection available during first setup, and allow downloads from Python.org, PyPI, GitHub release assets, and the Playwright browser CDN.
- If AI voices are unavailable, rerun Install.cmd and reopen the studio. Setup checks the voice pack and reports any missing Microsoft Visual C++ runtime required by ONNX; existing Windows voices remain a fallback.
- Read `logs/install.log` for setup errors or `logs/launch-*-error.log` for startup errors. Setup reports failure rather than creating a successful-install marker when a dependency or runtime check fails.
- Run Install.cmd again after fixing the issue. Existing valid downloads can be reused.
- Keep the complete app folder together. Do not launch the scripts from inside an unextracted ZIP.

To remove the app, run Stop.cmd, remove the desktop shortcut, and delete the application folder after keeping any projects and exports you need. There is no system-wide runtime to uninstall.

## Distribution and development

Run `powershell -NoProfile -ExecutionPolicy Bypass -File installer/package.ps1` from the project folder to build `dist/Tarkash-Video-Studio.zip`. This package includes application code, prepared assets, the default project, and the installer. It excludes the private runtime, source videos, analysis files, personal projects, logs, and exported videos. Each receiving machine downloads its own runtime on first setup.

For development, use Python 3.13, install requirements.txt in a virtual environment, run `python -m playwright install chromium` and `python scripts/setup_voices.py`, then run `python launch.py`. The voice dependency currently supports Python versions below 3.14. The installer uses a private Python runtime so it does not depend on the development environment.

The Windows installer pins [Python 3.13.17](https://www.python.org/downloads/release/python-31317/) and checks the [official 64-bit embeddable download](https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip) against the SHA-256 published on that release page. Pip is bootstrapped using [the official PyPA installer](https://pip.pypa.io/en/stable/installation/#get-pip-py). Application dependency versions are pinned in requirements.txt; their transitive dependencies are resolved by pip during installation.
