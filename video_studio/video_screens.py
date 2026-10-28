"""Opening and ending slide designs shared by previews and animated exports."""
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / 'video_design.css').read_text(encoding='utf-8')
DEFAULT_SMALL_DISCLAIMER = 'Stock market investments are subject to market risks. Information is for educational purposes only and is not investment advice.'
# Bootstrap Icons' Twitter bird, MIT licensed; see THIRD_PARTY_NOTICES.md.
TWITTER_PATH = 'M5.026 15c6.038 0 9.341-5.003 9.341-9.334q.002-.211-.006-.422A6.7 6.7 0 0 0 16 3.542a6.7 6.7 0 0 1-1.889.518 3.3 3.3 0 0 0 1.447-1.817 6.5 6.5 0 0 1-2.087.793A3.286 3.286 0 0 0 7.875 6.03a9.32 9.32 0 0 1-6.767-3.429 3.29 3.29 0 0 0 1.018 4.382A3.3 3.3 0 0 1 .64 6.575v.045a3.29 3.29 0 0 0 2.632 3.218 3.2 3.2 0 0 1-.865.115 3 3 0 0 1-.614-.057 3.28 3.28 0 0 0 3.067 2.277A6.6 6.6 0 0 1 .78 13.58a6 6 0 0 1-.78-.045A9.34 9.34 0 0 0 5.026 15'


def _e(value):
    return escape(str(value or ''), quote=True)


def _date(project):
    value = str(project.get('date', ''))
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d')
        suffix = 'th' if 11 <= parsed.day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(parsed.day % 10, 'th')
        return f'{parsed:%A, %B} {parsed.day}{suffix} {parsed:%Y}'.upper()
    except ValueError:
        return value.upper()


def _logo(brand, logo_uri):
    if logo_uri:
        return f'<img class="company-logo" src="{logo_uri}" alt="{_e(brand.get("name"))} logo">'
    return f'<div class="company-logo wordmark">{_e(brand.get("name"))}</div>'


def _disclaimer(brand):
    return str(brand.get('disclaimer') or '')


def _contacts(brand):
    parts = []
    for key, icon in [('website', '⌁'), ('phone', '✆'), ('email', '✉'), ('address', '⌖')]:
        value = brand.get(key)
        if value:
            parts.append(f'<div class="contact-row contact {"address" if key == "address" else ""}"><span class="contact-icon">{icon}</span><b>{_e(value).replace(chr(10), "<br>")}</b></div>')
    return ''.join(parts)


def _social_icons():
    icons = (
        ('Instagram', '<rect x="5" y="5" width="38" height="38" rx="11"/><circle cx="24" cy="24" r="9"/><circle class="icon-dot" cx="35.5" cy="12.5" r="2.5"/>'),
        ('Facebook', '<path class="icon-fill" d="M26.5 44V26.5h6l1-7h-7v-4.1c0-2.2.8-3.4 3.5-3.4H34V5.8c-1.7-.3-3.7-.5-5.6-.5-6.3 0-10.5 3.9-10.5 10.7v3.5h-5.8v7h5.8V44z"/>'),
        ('Twitter', f'<path class="icon-fill" d="{TWITTER_PATH}"/>'),
    )
    return '<div class="socials" aria-label="Social channels">' + ''.join(
        f'<span class="social-icon" aria-label="{name}"><svg viewBox="0 0 {16 if name == "Twitter" else 48} {16 if name == "Twitter" else 48}" aria-hidden="true">{path}</svg></span>'
        for name, path in icons
    ) + '</div>'


def opening_markup(project, brand, logo_uri):
    title = str(brand.get('introTitle') or project.get('title') or 'MORNING ACTION').split()
    first = title[0] if title else 'MORNING'
    second = ' '.join(title[1:]) if len(title) > 1 else 'ACTION'
    title_size = max(80, min(190, round(190 * 8 / max(8, len(first), len(second)))))
    rows = next((item.get('rows', []) for item in project.get('sections', []) if item.get('id') == 'indices'), [])
    first_row = rows[0] if rows else {}
    values = [first_row.get('nifty', '—'), first_row.get('sensex', '—'), first_row.get('bankNifty', '—')]
    ticker = ''.join(f'<div><small>{label}</small><b>{_e(value)}</b><span>↘</span></div>' for label, value in zip(('NIFTY', 'SENSEX', 'BANK NIFTY'), values))
    page = f'{section_page(project, brand, "intro"):02} / {section_total(project, brand):02}'
    return f'''<article class="slide slide-opening" style="--brand:{_e(brand.get('primary'))};--brand2:{_e(brand.get('secondary'))};--title-size:{title_size}px">
      <div class="open-top"><div class="open-logo">{_logo(brand, logo_uri)}</div><span class="open-edition">THE DAILY MARKET BRIEF <b>{page}</b></span></div>
      <div class="open-title-zone"><div class="open-side-label"><span class="pulse"></span>{_e(_date(project))}</div><div class="title-cluster"><span class="speed-lines"></span><span class="title-word morning">{_e(first)}</span><span class="title-word action">{_e(second)}<span class="title-arrow">↗</span></span><span class="language-tag">IN ENGLISH</span></div></div>
      <div class="opening-chart"><div class="chart-glow"></div></div>
      <div class="market-ticker">{ticker}</div>
      <div class="opening-news"><span class="pulse"></span><span class="news-label">TODAY'S OPENING CALL</span><p class="fit" data-min-font="25">{_e(project.get('intro'))}</p><div class="opening-news-foot"><span>MARKET OUTLOOK</span><strong>CAUTION <span>↘</span></strong></div></div>
      <div class="open-bottom"><span>INDICES</span><span class="dot"></span><span>TRENDS</span><span class="dot"></span><span>NEWS</span><span class="bottom-line"></span><b>01</b></div>
    </article>'''


def section_total(project, brand):
    content = project.get('insightsSections',project.get('sections',[])) if brand.get('layout')=='insights' and not brand.get('useSharedContent',False) else project.get('sections',[])
    return sum(1 for item in content if item.get('enabled', True)) + 2 + int(brand.get('includeDisclaimerPage', brand.get('endingStyle')=='disclaimer'))


def section_page(project, brand, kind):
    if kind == 'intro': return 1
    total = section_total(project, brand)
    return total if kind == 'ending' else total-1


def ending_markup(project, brand, logo_uri, kind='ending'):
    number = f'{section_page(project, brand, kind):02}'
    total = f'{section_total(project, brand):02}'
    disclaimer = _disclaimer(brand)
    logo = _logo(brand, logo_uri)
    if kind == 'disclaimer':
        long = 'long' if len(disclaimer) > 1000 else ''
        website = f'<span class="disclaimer-website">{_e(brand.get("website"))}</span>' if brand.get('website') else ''
        return f'''<article class="slide slide-disclaimer" style="--brand:{_e(brand.get('primary'))};--brand2:{_e(brand.get('secondary'))}">
          <div class="disclaimer-top"><div class="open-logo">{logo}</div><span>IMPORTANT INFORMATION</span></div>
          <div class="disclaimer-body {long}"><div class="disclaimer-number">{number} <i></i> {total}</div><span class="slide-kicker">PLEASE READ</span><h2>Market insight.<br><em>Informed decisions.</em></h2><div class="quote-mark">“</div><p class="fit" data-min-font="18">{_e(disclaimer)}</p><div class="disclaimer-rule"></div><span class="disclaimer-sig">EDUCATIONAL &amp; INFORMATIONAL USE ONLY</span></div>
          <div class="disclaimer-bottom">{website}<span>INVESTMENTS ARE SUBJECT TO MARKET RISKS</span></div>
        </article>'''
    contact = _contacts(brand)
    has_contact = any(brand.get(key) for key in ('website', 'phone', 'email', 'address'))
    socials = _social_icons()
    footer_note = f'<div class="brand-footer-note">{_e(brand["footer_note"]).replace(chr(10), "<br>")}</div>' if brand.get('footer_note') else ''
    legal_label = 'DISCLAIMER &amp; MARKET RISK NOTICE'
    legal_text = str(brand.get('smallDisclaimer') or DEFAULT_SMALL_DISCLAIMER)
    long = 'long' if len(legal_text) > 1000 else ''
    dense = 'dense' if len(str(brand.get('address') or '')) > 100 or brand.get('email') else ''
    label = f'CONNECT WITH {_e(brand.get("name")).upper()}' if has_contact else 'FOLLOW FOR MORE MARKET NEWS'
    empty = '' if has_contact else '<p class="no-contact">Independent insight for the next market session.</p>'
    return f'''<article class="slide slide-contact" style="--brand:{_e(brand.get('primary'))};--brand2:{_e(brand.get('secondary'))}">
      <div class="contact-top"><div class="contact-logo">{logo}</div><span>THANK YOU FOR WATCHING</span><h2>See the market<br><em>with clarity.</em></h2><p>Your morning briefing starts here.</p></div>
      <div class="contact-panel {dense}"><span class="contact-label">{label}</span>{contact}{empty}{socials}{footer_note}<div class="contact-panel-end"><span>FOLLOW THE NEXT SESSION</span><strong>↗</strong></div></div>
      <div class="contact-legal {long}"><span>{legal_label}</span><p class="disclaimer">{_e(legal_text)}</p></div>
      <div class="contact-bottom">MORNING ACTION <b>{number} / {total}</b></div>
    </article>'''


def screen_html(project, brand, kind, logo_uri, art_uri):
    css = CSS.replace("url('assets/opening-market-art.png')", f'url("{art_uri}")')
    # Direct render is at its natural 1080 x 1920 canvas, with no gallery wrapper.
    css += '\nhtml,body{width:1080px;height:1920px;margin:0;overflow:hidden}.slide{transform:none}'
    content = opening_markup(project, brand, logo_uri) if kind == 'intro' else ending_markup(project, brand, logo_uri, kind)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{content}</body></html>'
