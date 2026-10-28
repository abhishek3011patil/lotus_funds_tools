"""HTML slide composition and local H.264/AAC video rendering."""
import base64
import bisect
from functools import lru_cache
import html
from io import BytesIO
import json
import math
import mimetypes
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path
from PIL import Image

import imageio_ffmpeg
from playwright.sync_api import sync_playwright
from speech import synthesize, spoken_text, FLAGS
from intro_cover import opening_cover, COVER_CSS
from video_screens import screen_html, TWITTER_PATH

ROOT = Path(__file__).resolve().parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CONTENT_CSS = (ROOT / 'content_design.css').read_text(encoding='utf-8')

def local_asset(url):
    if not isinstance(url, str) or not url.startswith('/assets/'):
        return None
    p = (ROOT / url.lstrip('/')).resolve()
    if not p.is_relative_to((ROOT / 'assets').resolve()) or not p.is_file():
        return None
    return p

def data_uri(url):
    path = local_asset(url)
    if not path:
        return ''
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()


@lru_cache(maxsize=32)
def dark_background_logo(url):
    """Lift artwork off its baked white canvas for the dark opening slide."""
    path = local_asset(url)
    if not path:
        return ''
    with Image.open(path) as source:
        image = source.convert('RGBA')
    has_transparency = image.getchannel('A').getextrema()[0] < 250
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, original_alpha = pixels[x, y]
            # The supplied logos are mostly flattened onto white. Preserve the
            # anti-aliased edge as opacity rather than leaving a white rectangle.
            ink = 255 - min(r, g, b)
            alpha = original_alpha if has_transparency else round(original_alpha * ink / 255)
            if alpha < 4:
                pixels[x, y] = (255, 255, 255, 0)
                continue
            spread = max(r, g, b) - min(r, g, b)
            if spread < 35:
                pixels[x, y] = (245, 249, 251, alpha)
            else:
                peak = max(r, g, b)
                lift = max(0, 210 - peak)
                pixels[x, y] = (min(255, r + lift), min(255, g + lift), min(255, b + lift), alpha)
    output = BytesIO()
    image.save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()

def color(value, fallback):
    return value if re.fullmatch(r'#[0-9a-fA-F]{6}', str(value)) else fallback

def esc(text):
    return html.escape(str(text or ''))

def utf16_length(text):
    return len(str(text).encode('utf-16-le')) // 2


def styled_text(text, start, formats):
    end=start+utf16_length(text)
    boundaries={start,end}
    relevant=[]
    for mark in formats or []:
        if (isinstance(mark,dict) and mark.get('kind') in ('bold','italic','underline','strike','highlight','color','size')
            and isinstance(mark.get('start'),int) and isinstance(mark.get('end'),int)
            and mark['start']<end and mark['end']>start):
            relevant.append(mark)
            boundaries.add(max(start,mark['start']))
            boundaries.add(min(end,mark['end']))
    if not relevant:return esc(text)
    positions=[0]
    for character in text:positions.append(positions[-1]+(2 if ord(character)>0xFFFF else 1))
    output=[]
    edges=sorted(boundaries)
    for left,right in zip(edges,edges[1:]):
        active={mark['kind']:mark for mark in relevant if mark['start']<=left and mark['end']>=right}
        classes=' '.join('fmt-'+kind for kind in ('bold','italic','underline','strike','highlight') if kind in active)
        inline_css=[]
        selected_color=active.get('color',{}).get('value')
        if re.fullmatch(r'#[a-fA-F0-9]{6}',str(selected_color)):inline_css.append(f'color:{selected_color}')
        selected_size=active.get('size',{}).get('value')
        if type(selected_size) is int and 20<=selected_size<=60:inline_css.append(f'font-size:{selected_size}px')
        first=bisect.bisect_left(positions,left-start)
        last=bisect.bisect_left(positions,right-start)
        fragment=esc(text[first:last])
        attributes=(f' class="{classes}"' if classes else '')+(f' style="{";".join(inline_css)}"' if inline_css else '')
        output.append(f'<span{attributes}>{fragment}</span>' if attributes else fragment)
    return ''.join(output)


def paragraphs(text, line_styles=None, inline_formats=None):
    lines = []
    line_styles = line_styles or []
    offset=0
    active_list=None
    for index, line in enumerate(str(text).split('\n')):
        selected = line_styles[index] if index < len(line_styles) else 'auto'
        list_kind=selected if line.strip() and selected in ('ul','ol') else None
        if active_list!=list_kind:
            if active_list:lines.append(f'</{active_list}>')
            if list_kind:lines.append(f'<{list_kind} class="content-list">')
            active_list=list_kind
        if not line.strip():
            lines.append('<div class="gap"></div>')
        else:
            header = line.startswith('#') or (len(line) < 90 and line.upper() == line and any(c.isalpha() for c in line))
            without_hash=line.lstrip('#')
            leading=len(line)-len(without_hash)+len(without_hash)-len(without_hash.lstrip())
            display=without_hash.strip()
            classes = {'normal':'normal','heading1':'heading-one','heading2':'heading-two'}.get(selected, 'strong' if header else '')
            tag='li' if list_kind else 'div'
            lines.append(f'<{tag} class="line {classes}">{styled_text(display,offset+utf16_length(line[:leading]),inline_formats)}</{tag}>')
        offset+=utf16_length(line)+1
    if active_list:lines.append(f'</{active_list}>')
    return ''.join(lines)

def icon_svg(name):
    if name == 'twitter':
        return f'<svg viewBox="0 0 16 16" fill="currentColor"><path d="{TWITTER_PATH}"/></svg>'
    paths={
        'globe':'<circle cx="24" cy="24" r="20"/><ellipse cx="24" cy="24" rx="9" ry="20"/><path d="M4 24h40M8 13h32M8 35h32"/>',
        'phone':'<circle cx="24" cy="24" r="21"/><path d="M16 12l-4 5c1 10 9 18 19 19l5-5-8-6-4 4-6-6 4-4Z"/>',
        'pin':'<path d="M24 44S8 29 8 18a16 16 0 1 1 32 0c0 11-16 26-16 26Z"/><circle cx="24" cy="18" r="6"/>',
        'mail':'<rect x="4" y="10" width="40" height="29" rx="4"/><path d="m5 12 19 15 19-15"/>',
        'bell':'<path d="M10 34h28l-5-7V18a9 9 0 0 0-18 0v9Zm10 6h8M24 5v4"/>',
        'instagram':'<rect x="4" y="4" width="40" height="40" rx="12"/><circle cx="24" cy="24" r="10"/><circle cx="36" cy="12" r="2" fill="currentColor"/>',
        'facebook':'<circle cx="24" cy="24" r="21"/><path d="M28 12h-4q-5 0-5 6v26M12 24h18" stroke-width="5"/>'}
    return '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'+paths[name]+'</svg>'

def slide_html(project, brand, section):
    primary = color(brand.get('primary'), '#0750ae')
    accent = color(brand.get('accent'), '#632e38')
    logo = data_uri(brand.get('logo'))
    logo_html = f'<img class="logo" src="{logo}" alt="{esc(brand["name"])}">' if logo else f'<div class="wordmark">{esc(brand["name"])}</div>'
    kind = section['id']
    if kind == 'disclaimer' or (kind in ('intro', 'ending') and (brand.get('layout') != 'insights' or brand.get('endingStyle') == 'disclaimer') and not (kind == 'ending' and brand.get('endingStyle') == 'follow')):
        art = data_uri(brand.get('introImage', '/assets/market-intro.png'))
        safe_brand = {**brand, 'primary': primary, 'secondary': color(brand.get('secondary'), primary)}
        return screen_html(project, safe_brand, kind,
                           dark_background_logo(brand.get('logo')) if kind == 'intro' else logo, art)
    content = ''
    classes = ''
    if kind == 'intro':
        hero = data_uri(brand.get('introImage', '/assets/market-intro.png'))
        content = opening_cover(project, brand, logo_html, hero, primary)
        classes = 'morning-cover'
        if brand.get('layout')=='insights':
            content=f'<div class="insights-opening"><div class="insights-opening-title fit">{esc(brand.get("introTitle") or "INVESTING INSIGHTS")}</div><div class="insights-opening-date">{esc(project.get("date"))}</div><div class="insights-opening-logo">{logo_html}</div></div>'
            classes='insights-cover'
    elif kind == 'ending':
        style = brand.get('endingStyle', 'combined')
        details = [(brand.get('website'), 'globe'), (brand.get('phone'), 'phone'), (brand.get('email'), 'mail'), (brand.get('address'), 'pin')]
        contacts = ''.join(f'<div class="contact"><span>{icon_svg(icon)}</span><div>{esc(value)}</div></div>' for value, icon in details if value)
        socials = ' · '.join(x for x in [brand.get('instagram'), brand.get('facebook'), brand.get('twitter')] if x)
        full = style == 'disclaimer'
        content = f'<div class="ending-logo">{logo_html}</div><div class="ending-card {"disclaimer-only" if full else ""}"><div class="ending-inner fit">'
        if not full:
            if brand.get('ending_text'):
                content += f'<div class="ending-message">{esc(brand["ending_text"])}</div>'
            content += contacts + f'<div class="subscribe">{icon_svg("bell")} {esc(brand.get("socialText") or "SUBSCRIBE")}</div>'
            if brand.get('show_social_icons'):
                content += '<div class="social-icons">'+''.join(icon_svg(x) for x in ['instagram','facebook','twitter'])+'</div>'
            if socials:
                content += f'<div class="socials">{esc(socials)}</div>'
            if brand.get('footer_note'):
                content += f'<div class="footer-note">{esc(brand["footer_note"])}</div>'
        # Every style retains the full disclaimer; compact contact layout is still editable.
        content += f'<div class="disclaimer">{esc(brand.get("disclaimer", ""))}</div>'
        if full and brand.get('website'):
            content += f'<div class="disclaimer-website">{esc(brand["website"])}</div>'
        content += '</div></div>'
        classes = 'ending'
        if brand.get('endingStyle')=='follow':
            content=f'<div class="comic-kicker">DID YOU KNOW?</div><div class="comic-box fit">{esc(brand.get("ending_text", "FOLLOW FOR MORE MARKET NEWS!").replace("DID YOU KNOW?", "").strip())}</div><div class="comic-bell">{icon_svg("bell")}</div><div class="comic-note fit">{esc(brand.get("socialText") or "")}</div>'
            classes='insights-close'
    else:
        rows = section.get('rows', [])
        table = ''
        if rows:
            table = '<table><thead><tr><th>Metric</th><th>Nifty</th><th>Sensex</th><th>Bank Nifty</th></tr></thead><tbody>'
            for row in rows:
                table += '<tr>' + ''.join(f'<{"th" if key == "metric" else "td"}>{esc(row.get(key))}</{"th" if key == "metric" else "td"}>' for key in ['metric', 'nifty', 'sensex', 'bankNifty']) + '</tr>'
            table += '</tbody></table>'
        active = [item for item in project.get('sections', []) if item.get('enabled', True)]
        page = next((index + 2 for index, item in enumerate(active) if item['id'] == kind), 2)
        total = len(active) + 2 + int(brand.get('includeDisclaimerPage', brand.get('endingStyle')=='disclaimer'))
        footer = (f'<div class="standard-footer"><span>{esc(brand.get("name", ""))}</span>'
                  f'<i></i><span>MORNING ACTION</span><b>{page:02} / {total:02}</b></div>')
        content = f'<div class="corner top"></div><div class="corner bottom"></div><div class="content"><h1 class="fit heading-fit">{esc(section.get("title"))}</h1><div class="rule"></div><div class="fit body">{paragraphs(section.get("body", ""), section.get("lineStyles"), section.get("inlineFormats"))}{table}</div></div>{footer}'
        classes = 'standard'
        if brand.get('layout') == 'insights':
            art_url = brand.get('art', {}).get(section.get('sourceId', kind), '')
            art = data_uri(art_url)
            content = (f'<img class="insights-art" src="{art}">' if art else '<div class="insights-art"></div>') + f'<div class="insights-box"><h1 class="fit heading-fit">{esc(section.get("title"))}</h1><div class="fit body">{paragraphs(section.get("body", ""), section.get("lineStyles"), section.get("inlineFormats"))}{table}</div></div><div class="insights-disclaimer fit">{esc(brand.get("disclaimer", ""))}</div>'
            classes = 'insights'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:1920px;overflow:hidden}}body{{font-family:Arial,"Segoe UI",sans-serif;color:#202227;background:#fff;--primary:{primary};--accent:{accent};}}.slide{{position:relative;width:1080px;height:1920px;overflow:hidden}}.logo{{object-fit:contain;width:100%;height:100%}}.wordmark{{font-size:85px;font-weight:800;color:var(--primary);text-align:center}}.corner{{position:absolute;background:var(--primary);width:310px;height:300px;opacity:.9}}.top{{top:0;right:0;clip-path:polygon(0 0,100% 0,100% 100%,83% 25%)}}.bottom{{left:0;bottom:0;clip-path:polygon(0 0,15% 80%,100% 100%,0 100%)}}.corner:after{{content:"";position:absolute;inset:0;background:#ffffff55;clip-path:polygon(0 0,65% 10%,100% 100%)}}.content{{position:absolute;top:148px;left:76px;right:76px;bottom:140px}}h1{{font-size:46px;font-weight:800;color:var(--accent);margin:0 0 24px;text-align:center;line-height:1.18}}.rule{{height:2px;background:#999;margin-bottom:32px}}.body{{font-size:34px;line-height:1.36;font-weight:600;overflow-wrap:anywhere;white-space:normal}}.standard .body{{height:1480px}}.line{{white-space:pre-wrap}}.strong{{font-weight:800}}.gap{{height:.72em}}table{{border-collapse:collapse;table-layout:fixed;width:100%;margin-top:12px;font-size:.91em}}th,td{{border:2px solid #8c9299;padding:28px 13px;text-align:center;white-space:pre-wrap;overflow-wrap:anywhere}}th{{background:var(--primary);color:white;font-weight:700}}thead th:first-child{{background:#fff;color:#222}}td{{background:#fff;color:#222}}.intro-logo{{position:absolute;top:90px;left:230px;right:230px;height:190px}}.date{{position:absolute;top:330px;left:50px;right:50px;text-align:center;font-size:32px;font-weight:800;text-transform:uppercase;letter-spacing:2px}}.intro-title{{position:absolute;top:430px;left:70px;right:70px;text-align:center;font-size:52px;font-weight:800;color:var(--primary)}}.intro-copy{{position:absolute;z-index:2;top:540px;left:30px;right:30px;border-radius:45px;background:var(--primary);color:white;font-size:44px;font-weight:700;padding:52px;line-height:1.35;white-space:pre-wrap}}.intro-art{{position:absolute;bottom:0;left:0;width:100%;height:960px;object-fit:cover;mask-image:linear-gradient(transparent,black 22%)}}.chart-art{{position:absolute;bottom:70px;left:100px;color:var(--primary);font-size:190px;letter-spacing:13px;opacity:.4}}.ending-logo{{position:absolute;left:180px;right:180px;top:30px;height:250px}}.ending-card{{position:absolute;top:320px;left:16px;right:16px;bottom:0;border-radius:60px 60px 0 0;background:var(--primary);color:#fff;padding:72px 60px 38px}}.ending-card:before{{content:"";position:absolute;inset:0;opacity:.08;background:repeating-linear-gradient(145deg,transparent 0,transparent 90px,#fff 92px,#fff 94px);border-radius:inherit}}.ending-inner{{position:relative;height:100%;font-size:46px;font-weight:700;overflow-wrap:anywhere}}.contact{{display:flex;gap:45px;margin:25px 0 100px;line-height:1.3;white-space:pre-wrap}}.contact>span{{font-size:1.5em;width:90px;flex-shrink:0;text-align:center}}.subscribe{{text-align:center;font-size:.62em;letter-spacing:1px;margin:75px 0 65px}}.socials{{text-align:center;font-size:.65em;margin:40px 0}}.disclaimer{{font-size:.5em;line-height:1.35;text-align:center;font-weight:500;white-space:pre-wrap}}.disclaimer-only{{border-radius:0;top:270px;padding:125px 65px 70px}}.disclaimer-only .disclaimer{{font-size:1.36em;line-height:1.4}}.insights-art{{position:absolute;top:0;left:0;width:1080px;height:790px;object-fit:cover;background:var(--primary)}}.insights-box{{position:absolute;top:820px;left:72px;right:72px;bottom:205px;border-radius:48px;background:var(--primary);color:white;padding:40px 44px}}.insights-box h1{{font-size:43px;text-align:left;color:white}}.insights-box .body{{height:735px;font-size:35px}}.insights-box table{{font-size:.82em}}.insights-box th,.insights-box td{{padding:15px 8px}}.insights-disclaimer{{position:absolute;bottom:30px;left:80px;right:80px;height:145px;font-size:21px;font-weight:600;line-height:1.18;text-align:center}}
    .ending:has(.disclaimer-only) .ending-logo{{top:20px;height:220px}}.disclaimer-website{{text-align:center;font-size:.9em;margin-top:35px}}.standard th,.standard td{{padding-top:40px;padding-bottom:40px}}.insights-disclaimer{{height:160px;font-size:20.5px}}.contact svg{{width:74px;height:74px}}.subscribe{{display:flex;align-items:center;justify-content:center;gap:16px}}.subscribe svg{{width:40px;height:40px}}.social-icons{{display:flex;justify-content:space-around;margin:30px 30px 60px}}.social-icons svg{{width:110px;height:110px}}.footer-note{{font-size:.55em;font-weight:500;text-align:center;line-height:1.35;margin:30px 0;white-space:pre-wrap}}.ending-message{{font-size:1.35em;white-space:pre-wrap;text-align:center;margin-bottom:50px}}
    .insights-cover{{background:linear-gradient(140deg,#ffffff22,transparent 65%),var(--primary)}}.insights-cover:before{{content:"";position:absolute;inset:0;background:repeating-linear-gradient(120deg,transparent 0,transparent 110px,#ffffff0d 112px,#ffffff0d 115px)}}.insights-opening{{position:absolute;left:110px;right:110px;top:550px;border-radius:50px;background:white;padding:60px 60px 45px;text-align:center;box-shadow:0 25px 45px #0003}}.insights-opening-title{{font-size:95px;font-weight:700;line-height:1.5;letter-spacing:8px;color:var(--primary);border-bottom:12px solid var(--primary)}}.insights-opening-date{{font-size:30px;font-weight:800;margin:28px 0 80px}}.insights-opening-logo{{height:210px}}.insights-close{{background:repeating-conic-gradient(from 0deg at 50% 45%,#e8f5f7 0deg 8deg,#f7fcfd 8deg 16deg)}}.comic-kicker{{position:absolute;top:410px;left:180px;width:760px;transform:rotate(-7deg);font-size:100px;font-style:italic;line-height:1.05;font-weight:900;color:var(--primary)}}.comic-box{{position:absolute;top:700px;left:160px;width:760px;height:490px;border:24px solid var(--primary);background:white;box-shadow:35px 35px 0 #ffffffc9;transform:rotate(-7deg);display:flex;align-items:center;justify-content:center;text-align:center;font-size:80px;font-weight:900;padding:45px;line-height:1.4;white-space:pre-wrap;overflow-wrap:anywhere}}.comic-bell{{position:absolute;top:1390px;left:380px;width:320px;height:320px;border-radius:50%;background:var(--primary);color:#fff;padding:70px}}.comic-note{{position:absolute;bottom:65px;left:75px;right:75px;color:var(--primary);font-size:40px;text-align:center}}
    .content{{display:flex;flex-direction:column}}.standard .body{{flex:1;min-height:0;height:auto}}.insights-box{{display:flex;flex-direction:column}}.insights-box .body{{flex:1;min-height:0;height:auto}}.comic-note{{bottom:35px;height:140px}}.intro-title{{height:100px}}.intro-copy{{max-height:440px}}.heading-fit{{max-height:170px;flex-shrink:0}}.insights-opening-title{{max-height:400px}}
    {CONTENT_CSS}
    {COVER_CSS}
    </style></head><body><div class="slide {classes}">{content}</div></body></html>'''

def browser_options():
    options = {'headless': True}
    # The installer carries Chromium. Existing Chrome is a supported development fallback.
    candidates = [Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/Application/chrome.exe', Path('C:/Program Files/Google/Chrome/Application/chrome.exe'), Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')]
    if os.name == 'nt' and not (ROOT / '.runtime' / 'browsers').exists():
        for path in candidates:
            if path.exists():
                options['executable_path'] = str(path)
                break
    return options

class SlideBrowser:
    def __enter__(self):
        if (ROOT / '.runtime' / 'browsers').exists():
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.runtime' / 'browsers')
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(**browser_options())
        self.page = self.browser.new_page(viewport={'width':1080,'height':1920}, device_scale_factor=1)
        # Slide documents are self-contained; never fetch external content from a pasted asset URL.
        self.page.route('**/*', lambda route: route.abort())
        return self

    def capture(self, project, brand, section, path):
        self.page.set_content(slide_html(project, brand, section), wait_until='load')
        result = self.page.evaluate('''() => {for (const e of document.querySelectorAll('.fit')) {let size=parseFloat(getComputedStyle(e).fontSize);const minimum=Number(e.dataset.minFont)||22;while((e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2) && size>minimum){size=Math.max(minimum,size-.5);e.style.fontSize=size+'px';}if(e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2)return 'Text is too long for this slide. Shorten it or split into another section.';} return null;}''')
        if result:
            raise ValueError(f'{brand["name"]} / {section.get("title", section["id"])}: {result}')
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path))

    def capture_layers(self, project, brand, section, full_path):
        """Separate a still background and readable closing-page foreground."""
        self.capture(project, brand, section, full_path)
        base = full_path.with_name(full_path.stem + '-background.png')
        overlay = full_path.with_name(full_path.stem + '-foreground.png')
        kind = section['id']
        hide = {
            'intro': '.open-top,.open-title-zone,.market-ticker,.opening-news,.open-bottom',
            'ending': '.contact-top,.contact-panel,.contact-legal,.contact-bottom,.disclaimer-top,.disclaimer-body,.disclaimer-bottom',
            'disclaimer': '.contact-top,.contact-panel,.contact-legal,.contact-bottom,.disclaimer-top,.disclaimer-body,.disclaimer-bottom',
        }[kind]
        background_style = self.page.add_style_tag(content=hide + '{visibility:hidden!important}')
        self.page.screenshot(path=str(base))
        background_style.evaluate('(element) => element.remove()')
        foreground_style = self.page.add_style_tag(content='''
            html,body,.slide{background:transparent!important}
            .slide-opening::before,.slide-opening::after,
            .slide-contact::before,.slide-contact::after,
            .slide-disclaimer::before,.slide-disclaimer::after{display:none!important}
            .opening-chart{visibility:hidden!important}
        ''')
        self.page.screenshot(path=str(overlay), omit_background=True)
        foreground_style.evaluate('(element) => element.remove()')
        return base, overlay

    def capture_opening_layers(self, project, brand, section, full_path):
        """Capture independent artwork, header, title and two information cards."""
        self.capture(project, brand, section, full_path)
        base = full_path.with_name(full_path.stem + '-background.png')
        elements = '.open-top,.open-title-zone,.market-ticker,.opening-news,.open-bottom'
        hidden = self.page.add_style_tag(content=elements + '{visibility:hidden!important}')
        self.page.screenshot(path=str(base))
        hidden.evaluate('(element) => element.remove()')

        transparent = self.page.add_style_tag(content='''
            html,body,.slide{background:transparent!important}
            .slide-opening::before,.slide-opening::after{display:none!important}
            .opening-chart{visibility:hidden!important}
        ''')
        layers = [base]
        groups = (
            ('header', '.open-top,.open-side-label,.open-bottom'),
            ('title', '.title-cluster'),
            ('ticker', '.market-ticker'),
            ('call', '.opening-news'),
        )
        for name, visible in groups:
            mask = self.page.add_style_tag(content=(
                elements + '{visibility:hidden!important}' +
                visible + '{visibility:visible!important}'
            ))
            path = full_path.with_name(full_path.stem + '-' + name + '.png')
            self.page.screenshot(path=str(path), omit_background=True)
            mask.evaluate('(element) => element.remove()')
            layers.append(path)
        transparent.evaluate('(element) => element.remove()')
        return layers

    def __exit__(self, *args):
        self.browser.close()
        self.pw.stop()

def sections_for(project, brand):
    output = [{'id':'intro','title':project.get('title','Morning Action'),'body':project.get('intro',''),'duration':5,'silent':True}]
    active_sections=project.get('insightsSections',project['sections']) if brand.get('layout')=='insights' and not brand.get('useSharedContent',False) else project['sections']
    for section in active_sections:
        if not section.get('enabled', True):
            continue
        # Insights uses a shorter content area, so paginate without dropping any shared text.
        if brand.get('layout') == 'insights' and len(section.get('body','')) > 570 and not section.get('rows') and not section.get('narration','').strip():
            chunks=[]
            chunk_lines=[];chunk_styles=[];chunk_length=0
            saved_styles=section.get('lineStyles',[])
            def append_chunk():
                first=next((i for i,line in enumerate(chunk_lines) if line.strip()),None)
                if first is not None:
                    last=max(i for i,line in enumerate(chunk_lines) if line.strip())
                    chunks.append(('\n'.join(chunk_lines[first:last+1]).strip(),chunk_styles[first:last+1]))
            for line_index,line in enumerate(section['body'].split('\n')):
                if chunk_length+len(line)>570 and chunk_lines:
                    append_chunk();chunk_lines=[];chunk_styles=[];chunk_length=0
                chunk_lines.append(line)
                chunk_styles.append(saved_styles[line_index] if line_index<len(saved_styles) else 'auto')
                chunk_length+=len(line)+1
            append_chunk()
            cursor=0
            for index, (body, line_styles) in enumerate(chunks):
                item={**section,'id':section['id']+'-'+str(index+1),'sourceId':section['id'],'body':body,'lineStyles':line_styles,'title':section['title']+f' · {index+1}/{len(chunks)}','duration':float(section.get('duration',5))/len(chunks)}
                body_start=section['body'].find(body,cursor)
                if body_start>=0:
                    cursor=body_start+len(body)
                    start=utf16_length(section['body'][:body_start]);end=start+utf16_length(body)
                    item['inlineFormats']=[{**mark,'start':max(mark['start'],start)-start,'end':min(mark['end'],end)-start}
                        for mark in section.get('inlineFormats',[]) if mark['start']<end and mark['end']>start]
                # A custom full-section narration is kept on the first page only.
                if section.get('narration'):
                    item['narration']=section['narration'] if index==0 else ''
                    if index>0: item['silent']=True
                output.append(item)
        else:
            output.append(section.copy())
    separate=brand.get('includeDisclaimerPage', brand.get('endingStyle')=='disclaimer')
    closing_text=brand.get('ending_text','FOLLOW FOR MORE MARKET NEWS!') if brand.get('endingStyle')=='follow' else brand.get('disclaimer','')
    output.append({'id':'ending','title':'Company ending','body':closing_text,'duration':brand.get('endingDuration',10),'silent':bool(separate) or not project['settings'].get('readDisclaimer',False)})
    if separate:
        output.append({'id':'disclaimer','title':'Full-screen disclaimer','body':brand.get('disclaimer',''),'duration':brand.get('endingDuration',10),'silent':not project['settings'].get('readDisclaimer',False)})
    return output

def run_process(command, job, timeout=1800):
    if job.get('cancel'): raise InterruptedError('Export cancelled.')
    log = Path(job['_work']) / 'ffmpeg.log'
    with log.open('ab') as stream:
        proc=subprocess.Popen(command,stdout=stream,stderr=stream,creationflags=FLAGS)
        started=time.monotonic()
        while proc.poll() is None:
            if job.get('cancel') or time.monotonic()-started>timeout:
                proc.kill();proc.wait()
                if job.get('cancel'): raise InterruptedError('Export cancelled.')
                raise RuntimeError('Video processing timed out. See export log.')
            time.sleep(.2)
        if proc.returncode:
            raise RuntimeError('Video processing failed: '+log.read_text(errors='replace')[-2000:])


def video_filter(section_id, width, duration):
    """Keep slide artwork still and use a brief cut-safe fade."""
    height = round(width * 16 / 9)
    filters = [f'scale={width}:{height}']
    fade_duration = .45 if section_id in ('intro', 'ending', 'disclaimer') else .22
    filters.append(f'fade=t=in:st=0:d={fade_duration:.2f}')
    filters.append(f'fade=t=out:st={max(.3, duration-fade_duration):.3f}:d={fade_duration:.2f}')
    return ','.join(filters)


def layered_video_filter(section_id, width, duration):
    height = round(width * 16 / 9)
    return (
        f'[0:v]scale={width}:{height}[bg];'
        f'[1:v]scale={width}:{height},format=rgba[fg];'
        f"[bg][fg]overlay=x=0:y='H*0.035*pow(max(0,1-t/0.7),2)':eval=frame:format=auto:shortest=1,format=yuv420p,"
        f'fade=t=in:st=0:d=0.45,fade=t=out:st={max(.3,duration-.45):.3f}:d=0.45[v]'
    )


def opening_slide_filter(width, duration):
    """Slide the title and cards over a completely stationary market image."""
    height = round(width * 16 / 9)
    filters = [f'[0:v]scale={width}:{height}[base]']
    for index, name in enumerate(('header', 'title', 'ticker', 'call'), start=1):
        filters.append(f'[{index}:v]scale={width}:{height},format=rgba[{name}]')
    filters += [
        '[base][header]overlay=0:0:format=auto:shortest=1[s1]',
        "[s1][title]overlay=x='-W*pow(max(0,1-(t-0.4)/0.85),2)':y=0:eval=frame:format=auto:shortest=1[s2]",
        "[s2][ticker]overlay=x='W*pow(max(0,1-(t-1.25)/0.65),2)':y=0:eval=frame:format=auto:shortest=1[s3]",
        "[s3][call]overlay=x=0:y='H*pow(max(0,1-(t-1.85)/0.65),2)':eval=frame:format=auto:shortest=1,format=yuv420p,"
        f'fade=t=in:st=0:d=0.22,fade=t=out:st={max(.3,duration-.35):.3f}:d=0.35[v]',
    ]
    return ';'.join(filters)

def render_batch(project, selected, job):
    work=Path(job['_work']);work.mkdir(parents=True,exist_ok=True)
    settings=project['settings']; width=1080 if settings.get('quality')=='1080p' else 720
    total=sum(len(sections_for(project,b)) for b in selected);done=0
    with SlideBrowser() as browser:
        for brand in selected:
            segments=[]; manifest=[];offset=0
            for index, section in enumerate(sections_for(project,brand)):
                if job.get('cancel'): raise InterruptedError('Export cancelled.')
                job['message']=f'{brand["name"]} · {section.get("title") or "Closing disclaimer"}'
                image_path=work/f'{brand["id"]}-{index:02d}.png'
                standard_design = section['id'] == 'disclaimer' or ((brand.get('layout') != 'insights' or brand.get('endingStyle') == 'disclaimer') and not (section['id'] == 'ending' and brand.get('endingStyle') == 'follow'))
                if section['id'] == 'intro' and standard_design:
                    visual_paths = browser.capture_opening_layers(project,brand,section,image_path)
                    motion = 'opening'
                elif section['id'] in ('ending','disclaimer') and standard_design:
                    visual_paths = list(browser.capture_layers(project,brand,section,image_path))
                    motion = 'ending'
                else:
                    browser.capture(project,brand,section,image_path)
                    visual_paths = [image_path]
                    motion = 'still'
                duration=max(2,float(section.get('duration',5)))
                audio=None
                text=spoken_text(section)
                if settings.get('narration',True) and not section.get('silent') and text.strip():
                    audio,audio_duration=synthesize(text,settings,ROOT/'data'/'speech-cache')
                    duration=max(duration,audio_duration+.7)
                segment=work/f'{brand["id"]}-{index:02d}.mp4'
                command=[FFMPEG,'-y','-hide_banner','-loglevel','error']
                for visual in visual_paths:
                    command += ['-loop','1','-framerate','30','-i',str(visual)]
                command+=['-i',str(audio)] if audio else ['-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100']
                command+=['-t',str(round(duration,3))]
                if motion != 'still':
                    filter_graph = opening_slide_filter(width,duration) if motion == 'opening' else layered_video_filter(section['id'],width,duration)
                    command += ['-filter_complex',filter_graph,'-map','[v]','-map',f'{len(visual_paths)}:a']
                else:
                    command += ['-vf',video_filter(section['id'],width,duration)]
                command+=['-af','apad','-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p','-r','30','-threads','0','-c:a','aac','-ar','44100','-ac','2','-b:a','128k',str(segment)]
                run_process(command,job);segments.append(segment)
                manifest.append({'section':section['id'],'title':section.get('title'),'start':round(offset,3),'duration':round(duration,3),'narration':text if audio else ''})
                offset+=duration;done+=1;job['progress']=round(done/total*95)
            concat=work/(brand['id']+'-concat.txt')
            concat.write_text('\n'.join("file '"+s.name+"'" for s in segments),encoding='utf-8')
            filename=f'{brand["id"]}-{project["date"]}.mp4'
            target=work/filename
            music=local_asset(settings.get('music'))
            assembled=work/(brand['id']+'-assembled.mp4') if music else target
            run_process([FFMPEG,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(concat),'-c','copy','-movflags','+faststart',str(assembled)],job)
            if music:
                volume=max(0,min(.5,float(settings.get('musicVolume',.12))))
                run_process([FFMPEG,'-y','-hide_banner','-loglevel','error','-i',str(assembled),'-stream_loop','-1','-i',str(music),'-filter_complex',f'[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-movflags','+faststart',str(target)],job)
            (work/(brand['id']+'-timeline.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            job['outputs'].append({'name':brand['name'],'url':f'/outputs/{job["id"]}/{filename}','duration':round(offset,2)})
    job['progress']=100
    archive=work/'all-videos.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        for output in job['outputs']:
            path=work/output['url'].rsplit('/',1)[-1]
            z.write(path,path.name)
    job['zipUrl']=f'/outputs/{job["id"]}/all-videos.zip'
