# How to use Tarkash Video Studio

This guide is for the person preparing the daily edition or designing company versions. The studio creates portrait MP4 videos on a Windows 10/11 64-bit computer. The starting text and market figures are examples from 23 October 2026; check and update them before publishing.

## 1. Install and open

1. Extract the complete ZIP to a permanent folder, such as Documents. Do not run the installer inside the ZIP.
2. Open the extracted studio folder and double-click **Install.cmd**. Keep internet connected for this first setup. It installs a private runtime, rendering browser, video encoder, and AI voices; it may take several minutes. You do not need to install Python or buy a voice subscription.
3. The studio opens in your browser. Later, use the **Tarkash Video Studio** desktop shortcut or **Launch.cmd**. Keep the extracted folder in place. If you move it, run **Install.cmd** again.
4. When finished, double-click **Stop.cmd**. Wait for an export to finish before stopping the studio.

## 2. Edit the daily content

Open **Daily content**. Set the **Edition name** and **Publishing date**. Expand **Opening introduction** to change the sentence shown on the opening page. Use its **Preview opening** button to inspect it.

Use the slide tabs to edit the analysis, market trends, NIFTY/Sensex/Bank Nifty table, and two stock news pages. Change each **Slide headline** and **Slide content** as needed. The emoji button inserts an emoji at the cursor. On the market table page, edit the cells or use **Add a row** and the row delete buttons. **Include slide** lets you leave a slide out of the next export. **Minimum duration** sets a floor; the studio lengthens a slide automatically when narration needs more time.

The same shared content is used for each selected company. **Lotus Insights** can keep its separate script; choose it from **Content script**, or turn on **Use shared daily content** under that company in **Brands & endings**.

To format a paragraph like in Word, highlight any words in **Slide content** (or place the cursor on that line), then use **Style selected text**. Choose **Heading 1**, **Heading 2**, or **Normal text**. The style applies to the whole selected paragraph; select several lines to style them together. **Original design** restores the slide's automatic formatting. Check the preview before export, especially after making long lines into headings. Styling does not change the spoken words.

Edits save automatically on this computer. Check the **Saved locally** indicator before closing the browser.

## 3. Make the speaker pause naturally

For automatic narration, **leave Voice script blank** on the slide. The studio reads the headline, content, and market table, adding sentence breaks after headings, `|` separators, list lines, and table rows. These changes affect speech; the text displayed on the slide stays as entered.

To control the spoken wording yourself, enter a **Voice script** on that slide. A custom script replaces its automatic narration, so include any figures you want spoken. Put a **full stop**, **question mark**, or **exclamation mark** where you want a sentence break. A comma may create a shorter pause. A line break by itself may run together. For example:

> Nifty remains under pressure. Protect capital and wait for confirmation.

Choose **Voice for all companies** and press **Listen to voice** to compare a short fixed sample. That button reads a sample phrase, not your whole slide. In **Export studio**, the selected narrator is used for every company in the batch. Set **Speaking pace** to **-1** or **-2** if the narrator still sounds rushed. Natural voices include the Indian female choices Alpha, Ananya, Divya, and Priya, as well as US and British voices. They work offline after first setup. Always listen to the exported video to check names, numbers, and timing.

Voice and punctuation changes apply to **new exports**. Existing MP4 files do not change; generate the video again.

## 4. Set up company designs and endings

Open **Brands & endings** and pick a company. **Add brand** creates another company version; enter its name and details. **Replace logo** accepts PNG, JPG, or WebP. The studio selects primary and accent colors from colored parts of the logo, ignoring white, black, and gray. Use **Use logo colors** to select them again, or change the colors manually.

To remove a company, select it and click **Delete brand** at the bottom of its settings. Confirm the removal. It disappears from the saved company library and future exports; videos already generated remain in Export activity. Keep at least one company in the studio.

Choose the company's narrator if it should differ from the daily voice. Select an **Ending design**, then review the website, phone, email, office address, disclaimer, follow message, and social handles. The **Ending minimum duration** should allow enough time to read the disclaimer. Use **Preview ending** and the preview panel before export. Company colors appear throughout its video; the opening and closing pages animate while the content pages remain still.

The preview panel can switch both **company** and **slide**. It shows a frame from the video; it does not play the full animation or narration. Generate a test MP4 to review movement and sound together.

## 5. Export videos

Open **Export studio**. Tick the companies you want; use **Select all** only when you want the full batch. Choose **HD 720 × 1280** or **Full HD 1080 × 1920** as needed. Turn **Voice narration** on or off. If on, choose a narrator and speaking pace. **Read closing page aloud** is optional.

You can upload an MP3 or WAV background track that you have permission to use, adjust **Music volume**, or remove it. Keep the narration easy to hear.

Click **Generate selected videos**. Watch **Export activity** until it says completed, then use the MP4 download links. You can cancel a running batch. The generated files also stay in the studio's `outputs` folder. Export time depends on the computer, voice choice, video quality, and number of companies.

To clear old exports, choose **Delete batch permanently** on a finished batch and confirm. This removes its MP4 videos, ZIP download, and all working files from this computer. It does not change your saved daily content or company settings. A running batch must finish or be cancelled before it can be deleted. Use **Show older batches** to reach earlier exports.

## 6. Back up or move a project

Click **Save backup** to download a JSON copy of text and settings. **Import project** in Export studio replaces the current edition and company settings, so save a backup first. Uploaded logos and music are separate files in `assets/uploads`; copy that folder as well when moving a customized project to another computer. The studio saves its active project in `data/project.json` and its finished videos in `outputs`.

## If something is not working

- **Installer or voice setup failed:** keep internet connected, rerun **Install.cmd**, and read `logs/install.log` if it stops again.
- **Studio does not open:** double-click **Launch.cmd** and check `logs/launch-*-error.log` for the latest startup error.
- **Voice sounds too fast:** use sentence punctuation in a custom Voice script, or leave it blank for automatic breaks; set Speaking pace to -1 or -2 and export again.
- **Export takes too long:** select only the companies you need. Editing text or changing voices takes additional time because new speech must be made; unchanged speech is reused on later exports. Keep the required resolution and slide durations for the published version.
- **Text does not fit a slide:** shorten it or divide it between sections. A long voice script does not create a new visual page automatically.
- **Preview is blank:** add a publishing date, then press **Try preview again**.
- **An old MP4 still sounds unchanged:** create a new export after editing. Previously generated files stay as they were.

For technical setup and component details, see `README.md` and `THIRD_PARTY_NOTICES.md` in the same folder.
