import panflute as pf
import re
import hashlib
import io
import json
import os
import sys
from typing import Any


def metadata_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return pf.stringify(value)


def snake_case(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    return text or "untitled"


def doc_to_markdown(doc: pf.Doc) -> str:
    json_buf = io.StringIO()
    pf.dump(doc, output_stream=json_buf)
    markdown = pf.convert_text(
        json_buf.getvalue(),
        input_format="json",
        output_format="markdown",
    )
    return markdown


def prepare(doc: pf.Doc) -> None:
    pattern_meta = doc.get_metadata("split-pattern", None)
    if pattern_meta is None:
        raise ValueError("No split-pattern metadata provided.")

    pattern_str = metadata_to_str(pattern_meta)
    doc.split_regex = re.compile(pattern_str)

    # Capture source file (user-provided metadata; optional)
    source_file_meta = doc.get_metadata("source-file", None)
    doc.source_file = metadata_to_str(source_file_meta).strip() or None

    # Stable source hash based on full source content
    full_text = pf.stringify(doc)
    doc.source_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    doc.source_hash6 = doc.source_hash[:6]

    doc.current_blocks: list[pf.Element] = []
    doc.sections: list[dict[str, Any]] = []
    doc.current_title: str | None = None
    doc.section_index = 1  # 1-based section numbering
    doc.split_count = 0
    output_meta = metadata_to_str(doc.get_metadata("ndjson-output-file", None)).strip()
    doc.ndjson_output_file = output_meta or os.environ.get("SPLIT_SECTIONS_NDJSON_FILE", "").strip()


def finalize_section(doc: pf.Doc) -> None:
    if not doc.current_blocks:
        return

    slug = snake_case(doc.current_title)
    filename = f"{slug}_{doc.source_hash6}.md"

    section_doc = pf.Doc(*doc.current_blocks)
    markdown = doc_to_markdown(section_doc)

    record: dict[str, Any] = {
        "source_file": doc.source_file,
        "source_hash": doc.source_hash,
        "source_hash6": doc.source_hash6,
        "section_index": doc.section_index,
        "section_title": doc.current_title,
        "section_slug": slug,
        "metadata": {
            "filename": filename,
        },
        "content": markdown,
    }

    doc.sections.append(record)
    doc.current_blocks.clear()
    doc.section_index += 1


def action(block: pf.Element, doc: pf.Doc):
    if not isinstance(block, pf.Block):
        return None

    text = pf.stringify(block).strip()

    # Split boundary: any block whose stringified text matches the regex.
    if text and doc.split_regex.search(text):
        doc.split_count += 1
        # Close previous section, if one has started.
        if doc.current_title is not None:
            finalize_section(doc)

        # Start a new section; title is marker text with split token removed.
        section_title = doc.split_regex.sub("", text, count=1).strip()
        doc.current_title = section_title or f"section_{doc.section_index}"

        # Keep the split entity as the first block of the new section
        doc.current_blocks.append(block)
        return []

    # Ignore preamble blocks before the first split marker so that one marker
    # produces one output record.
    if doc.current_title is not None:
        doc.current_blocks.append(block)
    return []


def finalize(doc: pf.Doc) -> None:
    if doc.current_title is not None:
        finalize_section(doc)

    # Write NDJSON side output without corrupting pandoc's filter JSON protocol.
    if doc.ndjson_output_file:
        with open(doc.ndjson_output_file, "w", encoding="utf-8") as f:
            for record in doc.sections:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return

    # Fallback: write NDJSON to stderr.
    for record in doc.sections:
        sys.stderr.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(doc=None):
    return pf.run_filter(action, prepare=prepare, finalize=finalize)


if __name__ == "__main__":
    main()
