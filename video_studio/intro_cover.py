"""Editable logo, date and briefing above the original Morning Action artwork."""
from datetime import datetime
from html import escape


def readable_palette(primary):
    rgb = tuple(int(primary[i:i + 2], 16) for i in (1, 3, 5))

    def luminance(values):
        values = [v / 255 for v in values]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))

    background_luminance = luminance(rgb)
    white_contrast = 1.05 / (background_luminance + .05)
    dark_contrast = (background_luminance + .05) / (luminance((16, 43, 51)) + .05)
    ink = '#ffffff' if white_contrast >= dark_contrast else '#102b33'
    heading = rgb
    while 1.05 / (luminance(heading) + .05) < 4.5:
        heading = tuple(round(value * .9) for value in heading)
    return ink, '#' + ''.join(f'{value:02x}' for value in heading)


def opening_cover(project, brand, logo, hero, primary):
    date = str(project.get('date', ''))
    try:
        parsed = datetime.strptime(date, '%Y-%m-%d')
        suffix = 'th' if 11 <= parsed.day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(parsed.day % 10, 'th')
        date = f'{parsed:%A, %B} {parsed.day}{suffix} {parsed:%Y}'
    except ValueError:
        pass
    title_text = str(brand.get('introTitle') or project.get('title') or 'MORNING ACTION')
    title = escape(title_text)
    opening_text = escape(str(project.get('intro', '')))
    ink, heading = readable_palette(primary)
    # The reference already contains the orange title and its white-to-chart
    # fade. Display it whole for the original title, with no duplicate heading.
    reference = brand.get('introImage', '/assets/market-intro.png') in (
        '/assets/market-intro.png', '/assets/morning-action-art.png')
    original_title = ' '.join(title_text.casefold().split()) in ('morning action', 'morning action in english')
    original_art = bool(hero and reference and original_title)
    if hero:
        art_class = 'reference-art' if original_art else 'custom-title-art' if reference else 'custom-art'
        alt = 'Morning Action in English' if original_art else ''
        art = f'<div class="cover-art {art_class}"><img src="{hero}" alt="{alt}"></div>'
    else:
        art = '<div class="cover-art cover-fallback" aria-hidden="true"><div class="cover-bars">▂ ▄ ▃ ▅ ▄ ▆ █</div></div>'
    custom_title = '' if original_art else f'<div class="cover-custom-title"><div class="fit" data-min-font="48">{title}</div></div>'
    return f'''{art}{custom_title}<div class="cover-top" style="--cover-ink:{ink};--cover-heading:{heading}">
        <div class="cover-logo fit" data-min-font="30">{logo}</div>
        <div class="cover-date fit" data-min-font="24">{escape(date)}</div>
        <div class="cover-brief fit" data-min-font="30">{opening_text}</div>
    </div>'''


COVER_CSS = '''
.morning-cover{background:#fff}
.cover-top{position:absolute;z-index:2;top:0;left:0;right:0;height:640px;background-color:#fff;background-image:linear-gradient(#e6e6e6 2px,transparent 2px),linear-gradient(90deg,#e6e6e6 2px,transparent 2px);background-size:112px 112px;background-position:0 -34px,72px 0}
.cover-logo{position:absolute;top:35px;left:130px;right:130px;height:210px;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:70px}
.cover-logo .logo{display:block;width:500px;max-width:100%;height:210px;object-fit:contain;mix-blend-mode:multiply}
.cover-logo .wordmark{font-size:inherit;max-width:100%;overflow-wrap:anywhere;color:var(--cover-heading)}
.cover-date{position:absolute;top:266px;left:36px;right:36px;height:62px;color:#080808;font-size:40px;line-height:1.3;font-weight:700;text-transform:uppercase;white-space:nowrap;text-align:center;align-content:center}
.cover-brief{position:absolute;top:344px;left:0;right:0;height:296px;border:4px solid #101820;border-radius:50px;padding:36px 60px;background:var(--primary);color:var(--cover-ink);font-size:48px;line-height:1.4;font-weight:700;text-align:center;align-content:center;white-space:pre-wrap;overflow-wrap:anywhere}
.cover-art{position:absolute;left:0;right:0;top:640px;bottom:0;overflow:hidden;background:#fff}
.cover-art img{position:absolute;left:50%;bottom:0;transform:translateX(-50%);max-width:none}
.cover-art.reference-art img{height:100%;width:100%;object-fit:contain}
.cover-art.custom-title-art img{height:190%;width:auto;min-width:100%}
.cover-art.custom-art img{height:100%;width:100%;object-fit:cover;object-position:center}
.cover-art.custom-title-art:after,.cover-art.custom-art:after{content:"";position:absolute;inset:0;background:linear-gradient(to bottom,#fff 0%,#ffffffed 28%,#ffffff75 43%,transparent 60%)}
.cover-custom-title{position:absolute;z-index:1;top:710px;left:155px;right:110px;transform:skewY(-7deg);color:#d74b00;font-family:Impact,"Arial Narrow",Arial,sans-serif;font-size:166px;font-weight:400;line-height:1.1;text-align:center}
.cover-custom-title>.fit{height:430px;align-content:center;white-space:pre-wrap;overflow-wrap:anywhere}
.cover-fallback{background:linear-gradient(170deg,#f0f4fa,var(--primary))}
.cover-bars{position:absolute;bottom:60px;left:30px;right:30px;font-size:180px;letter-spacing:5px;color:#ffffff7a;white-space:nowrap}
'''
