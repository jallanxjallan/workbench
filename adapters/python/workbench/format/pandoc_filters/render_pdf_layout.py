import sys
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import panflute as pf

ANNOTATION_COLORS = {
    '¶': (255, 255, 255),       # white box
    '🖼️': (230, 240, 255),      # light blue
    '⬖': (255, 245, 200),      # light yellow
    '❝ ❞': (240, 230, 255),    # lavender
    '▌': (200, 255, 230),      # mint
}

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 18
PADDING = 20
LINE_SPACING = 6


def draw_annotations(image_path, annotations):
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except IOError:
        font = ImageFont.load_default()

    y = PADDING
    for ann in annotations:
        text = ann['text']
        symbol = ann['symbol']
        box_color = ANNOTATION_COLORS.get(symbol, (255, 255, 255))
        w, h = draw.textsize(text, font=font)

        box_height = h + PADDING // 2
        box_width = image.width - 2 * PADDING

        draw.rectangle([PADDING, y, PADDING + box_width, y + box_height], fill=box_color + (200,), outline=(0, 0, 0))
        draw.text((PADDING + 10, y + PADDING // 4), text, fill=(0, 0, 0), font=font)
        y += box_height + LINE_SPACING

    return Image.alpha_composite(image, overlay).convert("RGB")


def render_layout_pdf(layout, output_pdf_path):
    pages = {}
    for item in layout:
        page = item['page']
        pages.setdefault(page, []).append(item)

    rendered_pages = []
    for page_path, annotations in pages.items():
        annotated = draw_annotations(page_path, annotations)
        rendered_pages.append(annotated)

    if rendered_pages:
        rendered_pages[0].save(output_pdf_path, save_all=True, append_images=rendered_pages[1:])
        print(f"[layout render] wrote PDF to {output_pdf_path}")
    else:
        print("No pages rendered. Exiting.")


def prepare(doc):
    if not doc.get_metadata("layout-data"):
        output_path = doc.get_metadata("outputfile")
        if output_path and str(output_path).endswith(".pdf"):
            sys.stderr.write("\033[91mError: PDF output requested but no layout-data present.\033[0m\n")
            sys.exit(1)
        pf.debug("No layout-data in metadata; skipping PDF renderer.")
        return None

    output_path = doc.get_metadata("outputfile")
    if not output_path:
        pf.debug("Missing 'outputfile' metadata for renderer.")
        sys.exit(1)

    layout_meta = doc.get_metadata("layout-data", default=[])
    layout = [
        {
            "page": pf.stringify(entry["page"]),
            "symbol": pf.stringify(entry["symbol"]),
            "text": pf.stringify(entry["text"])
        }
        for entry in layout_meta
    ]

    render_layout_pdf(layout, output_path)
    sys.exit(0)


def main(doc=None):
    return pf.run_filter(None, prepare=prepare, finalize=None, doc=doc)


if __name__ == "__main__":
    main()
