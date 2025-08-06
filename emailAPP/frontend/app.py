import os
from bs4 import BeautifulSoup
from PIL import Image
from collections import Counter

logos_folder = "logos"
html_template_path = "template.html"
output_folder = "output_htmls"
css_variable = "--choose-your-specific-name"

os.makedirs(output_folder, exist_ok=True)

def is_near_black(rgb, threshold=50):
    r, g, b = rgb
    return r < threshold and g < threshold and b < threshold

def get_dominant_color(image_path):
    with Image.open(image_path) as img:
        img = img.convert("RGB").resize((50, 50))
        pixels = [p for p in img.getdata() if not is_near_black(p)]
        if not pixels:
            return "#cccccc"
        most_common = Counter(pixels).most_common(1)[0][0]
        return '#%02x%02x%02x' % most_common

with open(html_template_path, "r", encoding="utf-8") as file:
    html_content = file.read()

for logo_file in os.listdir(logos_folder):
    if not logo_file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        continue

    soup = BeautifulSoup(html_content, 'html.parser')

    logo_tag = soup.find("img", id="logoofcompany")
    if logo_tag:
        logo_tag['src'] = os.path.join(logos_folder, logo_file).replace('\\', '/')
    else:
        print("❌ <img id='logoofcompany'> not found")
        continue

    dominant_color = get_dominant_color(os.path.join(logos_folder, logo_file))

    # ✅ Only update variable inside :root block
    for style in soup.find_all("style"):
        lines = style.text.splitlines()
        in_root = False
        new_lines = []

        for line in lines:
            if ":root" in line:
                in_root = True
            elif "}" in line and in_root:
                in_root = False

            if css_variable in line and in_root:
                line = f"      {css_variable}: {dominant_color};"

            new_lines.append(line)

        style.string = "\n".join(new_lines)

    base_name = os.path.splitext(logo_file)[0].replace("logo_", "")
    output_path = os.path.join(output_folder, f"{base_name}.html")
    with open(output_path, "w", encoding="utf-8") as out_file:
        out_file.write(str(soup))

    print(f"✅ Generated {output_path} with h1 background → {dominant_color}")
