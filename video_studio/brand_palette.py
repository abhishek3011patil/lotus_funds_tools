"""Pick usable brand colors from a logo, ignoring black, white and gray."""
import colorsys
from collections import defaultdict

from PIL import Image


def _hex(hsv):
    rgb = colorsys.hsv_to_rgb(*hsv)
    return '#' + ''.join(f'{round(channel * 255):02X}' for channel in rgb)


def extract_palette(source: Image.Image):
    image = source.convert('RGBA')
    image.thumbnail((240, 240))
    groups = defaultdict(list)
    for r, g, b, alpha in image.getdata():
        if alpha < 80:
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if saturation < .24 or value < .12 or value > .94:
            continue
        groups[int(hue * 24) % 24].append((hue, saturation, value, alpha / 255))
    if not groups:
        return None
    ranked = sorted(groups, key=lambda bin: sum(pixel[1] * pixel[3] for pixel in groups[bin]), reverse=True)

    def color_of(bin):
        pixels = groups[bin]
        weight = sum(pixel[3] for pixel in pixels)
        hue = sum(pixel[0] * pixel[3] for pixel in pixels) / weight
        saturation = max(.48, min(.87, sum(pixel[1] * pixel[3] for pixel in pixels) / weight))
        value = max(.37, min(.72, sum(pixel[2] * pixel[3] for pixel in pixels) / weight))
        return hue, saturation, value

    primary = color_of(ranked[0])
    lead_weight = sum(pixel[1] * pixel[3] for pixel in groups[ranked[0]])
    companion = next((bin for bin in ranked[1:]
                      if min((bin - ranked[0]) % 24, (ranked[0] - bin) % 24) >= 2
                      and sum(pixel[1] * pixel[3] for pixel in groups[bin]) >= lead_weight * .22), None)
    if companion is None:
        secondary = (primary[0], max(.42, primary[1] * .8), min(.83, primary[2] + .17))
    else:
        secondary = color_of(companion)
    return {'primary': _hex(primary), 'secondary': _hex(secondary), 'accent': _hex(secondary)}
