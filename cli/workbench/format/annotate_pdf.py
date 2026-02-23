#!/home/jeremy/Python3.13Env/bin/python
"""
annotate_pdf.py
----------------

Process a layout master PDF containing annotations with layout symbols.

Usage:
    ./annotate_pdf.py input.pdf

Behavior:
    • Every annotation must begin with a recognized layout symbol.
    • ¶ (running_text):
        - Payload must be a Markdown link or file path to a .md file.
        - The file contents are inserted as a popup annotation (raw text).
        - If the file is missing or unreadable, processing stops immediately
          and only that page is saved as <basename>_pageN_error.pdf.
    • Other symbols (🖼️, ⧉, ▌, ⬖, 📐, ⌘, 📖):
        - Payload text is converted to a FreeText annotation.
        - The note is prefixed with LABEL: payload (uppercase label).
        - Text is wrapped at ~80 characters, larger font, light cream background,
          solid border for readability.
    • If all annotations are valid, a complete annotated PDF is written as
      <basename>_annotated.pdf.

Symbols supported:
    ¶   running_text      (parse filepath, insert file contents in popup)
    🖼️  caption
    ⧉   boxout
    ▌   sidebar
    ⬖   standalone_page
    📐  layout_note
    ⌘   page_title
    📖  pdf_page

Requirements:
    pip install pymupdf tqdm

Notes:
    • Progress bar via tqdm shows page processing.
    • Errors stop processing immediately for faster debugging.
    • Popup contents are left raw (no wrapping) to ensure fidelity when copy-
      pasting into design tools like InDesign.
"""

import fitz  # PyMuPDF
import sys
import re
import textwrap
from pathlib import Path
from tqdm import tqdm
from document.vault_document import Document

# -------------------------
# Config
# -------------------------

symbol_refs = {
    '¶': 'running_text',
    '🖼️': 'caption',
    '⧉': 'boxout',
    '▌': 'sidebar',
    '⬖': 'standalone_page',
    '📐': 'layout_note',
    '⌘': 'page_title',
    '📖': 'pdf_page',
}

link_pattern = re.compile(r"\[.*?\]\((.*?)\)")


# -------------------------
# Helpers
# -------------------------

def progress_iter(iterable, desc="Working"):
    """Wrap any iterable with a tqdm progress bar."""
    return tqdm(iterable, total=len(iterable), desc=desc)


def safe_set_icon(annot, icon_name: str):
    """Set annotation icon across PyMuPDF versions."""
    try:
        annot.set_icon(icon_name)
    except AttributeError:
        try:
            annot.set_info(info={"icon": icon_name})
        except Exception:
            pass


# -------------------------
# Formatting functions
# -------------------------

def make_popup_annotation(page, rect, text, wc):
    """Popup sticky-note with replacement text (raw, not wrapped)."""
    padded_text = "\n" + text + "\n"
    annot = page.add_text_annot(rect.tl, padded_text)
    safe_set_icon(annot, "Note")
    annot.set_flags(0)

    base_width = 400
    base_height = 300
    extra_height = (wc // 100) * 60
    popup_rect = fitz.Rect(
        rect.x0 + 20,
        rect.y0 - 20,
        rect.x0 + base_width,
        rect.y0 + base_height + extra_height,
    )
    annot.set_popup(popup_rect)
    annot.update()


def make_error_annotation(page, rect, msg, page_num):
    """Popup annotation for errors, includes page number."""
    padded_msg = f"*** ERROR on page {page_num} ***\n{msg}\n*** ERROR ***"
    annot = page.add_text_annot(rect.tl, padded_msg)
    safe_set_icon(annot, "Cross")
    annot.set_flags(0)
    annot.update()


def make_symbol_annotation(page, rect, symbol: str, payload: str):
    """FreeText annotation for non-¶ symbols with label + wrapped payload."""
    label = symbol_refs.get(symbol, "UNKNOWN").upper()
    note_text = f"{label}: {payload}" if payload else label

    # Wrap text to ~80 chars per line
    wrapped_lines = textwrap.wrap(note_text, width=80)
    wrapped_text = "\n".join(wrapped_lines)

    fontsize = 13
    line_height = fontsize * 1.5
    n_lines = len(wrapped_lines)

    # Box size based on wrapped text
    wrap_width = 400
    frect = fitz.Rect(
        rect.x0,
        rect.y0,
        rect.x0 + wrap_width,
        rect.y0 + n_lines * line_height,
    )

    # Add generous padding
    padding = 10
    frect = fitz.Rect(
        frect.x0 - padding,
        frect.y0 - padding,
        frect.x1 + padding,
        frect.y1 + padding,
    )

    annot = page.add_freetext_annot(
        frect,
        wrapped_text,
        fontsize=fontsize,
        fontname="helv",
        text_color=(0, 0, 0),
        fill_color=(1, 0.97, 0.85),   # light cream background
        align=0,
    )
    annot.set_border(width=1.0)
    annot.update(
        text_color=(0.3, 0.3, 0.3),  # FreeText: same effect as border_color
        # border_color=(0.3, 0.3, 0.3),  # equivalent to text_color for FreeText
        # fill_color=(1, 1, 1),          # optional background; False for transparent
    )

    annot.update()


def save_error_page(doc, pdf_path, page_num):
    """Save only the error page into a standalone PDF."""
    single_doc = fitz.open()
    single_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
    out_path = f"{Path(pdf_path).with_suffix('')}_page{page_num}_error.pdf"
    single_doc.save(out_path)
    single_doc.close()
    return out_path


# -------------------------
# Main processing
# -------------------------

def replace_annotations_with_text(pdf_path: str):
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(progress_iter(doc, desc="Annotating"), start=1):
        for annot in list(page.annots() or []):
            raw_text = annot.info.get("content", "").strip()
            if not raw_text:
                continue

            rect = annot.rect
            page.delete_annot(annot)
            symbol = raw_text[0]

            if symbol not in symbol_refs:
                msg = f"Unrecognized symbol '{symbol}' in annotation: {raw_text}"
                make_error_annotation(page, rect, msg, page_num)
                out_path = save_error_page(doc, pdf_path, page_num)
                doc.close()
                return False, out_path, [(page_num, msg)]

            payload = raw_text[1:].strip()

            if symbol == '¶':
                # Parse Markdown link if present
                m = link_pattern.search(payload)
                filepath = m.group(1) if m else payload

                file = Path(filepath)
                if file.is_file():
                    try:
                        md_doc = Document.read_file(file)
                        text = md_doc.content.strip()
                        wc = md_doc.word_count()
                        make_popup_annotation(page, rect, text, wc)
                    except Exception as e:
                        msg = f"Cannot read {filepath}: {e}"
                        make_error_annotation(page, rect, msg, page_num)
                        out_path = save_error_page(doc, pdf_path, page_num)
                        doc.close()
                        return False, out_path, [(page_num, msg)]
                else:
                    msg = f"File not found: {filepath}"
                    make_error_annotation(page, rect, msg, page_num)
                    out_path = save_error_page(doc, pdf_path, page_num)
                    doc.close()
                    return False, out_path, [(page_num, msg)]
            else:
                make_symbol_annotation(page, rect, symbol, payload)

    upload_dir = Path('/home/jeremy/Uploads')
    base = upload_dir.joinpath(pdf_path).with_suffix("")
    output_path = f"{base}_annotated.pdf"
    doc.save(output_path)
    doc.close()
    return True, output_path, []


# -------------------------
# Entry point
# -------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: annotate_pdf.py input.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    success, saved_path, errors = replace_annotations_with_text(pdf_path)

    if not success:
        print(f"❌ Error encountered on page {errors[0][0]}. Debug page saved to {saved_path}")
        for page_num, err in errors:
            print(f"  - Page {page_num}: {err}")
        sys.exit(2)
    else:
        print(f"✅ Updated PDF saved to {saved_path}")
