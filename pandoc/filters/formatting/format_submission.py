#!/home/jeremy/Python3.12Env/bin/python
# -*- coding: utf-8 -*-
#
# check_content_links.py — Markdown content link validator
#

import panflute as pf
import attr

mode = 'layout'
handlers = {}
components = set()


definitions = {
    '¶': {
        'key': 'running',
        'layout': {
            'before': 'break_before',
            'after': 'break_after',
        },
        'review': {
            'wrap': 'running_review'
        }
    },
    '🖼️': {
        'key': 'caption',
        'layout': {
            'before': 'before_wrapper',
            'after': 'after_wrapper',
        },
        'review': {
            'wrap': 'caption_review'
        }
    },
    '⧉': {
        'key': 'boxout',
        'layout': {
            'before': 'boxout_start',
            'after': 'boxout_end',
        },
        'review': {
            'wrap': 'boxout_review'
        }
    },
    '▌': {
        'key': 'sidebar',
        'layout': {
            'before': 'sidebar_start',
            'after': 'sidebar_end',
        },
        'review': {
            'wrap': 'sidebar_review'
        }
    },
    '❝ ❞': {
        'key': 'pull_quote',
        'layout': {
            'before': 'quote_intro',
            'after': 'quote_outro',
        },
        'review': {
            'wrap': 'quote_review'
        }
    },
    '⬖': {
        'key': 'standalone_page',
        'layout': {
            'before': 'standalone_start',
            'after': 'standalone_end',
        },
        'review': {
            'wrap': 'standalone_review'
        }
    },
    '📐': {
        'key': 'layout_note',
        'layout': {
            'before': 'note_intro',
            'after': 'note_outro',
        },
        'review': {
            'wrap': 'layoutnote_review'
        }
    },
    '⌘': {
        'key': 'page_title',
        'layout': {
            'before': 'title_start',
            'after': 'title_end',
        },
        'review': {
            'wrap': 'title_review'
        }
    },
    '📖': {
        'key': 'pdf_page',
        'layout': {
            'before': 'pdf_marker',
            'after': 'pdf_marker',
        },
        'review': {
            'wrap': 'pdfpage_review'
        }
    }
}


@attr.define
class SymbolHandler:
    symbol: str
    key: str
    layout: dict = attr.field(factory=dict)
    review: dict = attr.field(factory=dict)

    def get_style(self, mode: str, kind: str):
        return getattr(self, mode, {}).get(kind)


def load_definitions():
    for sym, spec in definitions.items():
        handlers[sym] = SymbolHandler(symbol=sym, **spec)


def resolve_components(meta_list):
    """
    Accepts symbols or lowercase key names. Warns if unrecognized. Supports '*' wildcard.
    """
    if not meta_list or '*' in meta_list:
        pf.debug("Wildcard '*' found or empty components list — enabling all components.")
        return set(definitions.keys())

    resolved = set()
    keys_to_symbols = {v['key'].lower(): sym for sym, v in definitions.items()}
    known_symbols = set(definitions.keys())

    for item in meta_list:
        if item in known_symbols:
            resolved.add(item)
        else:
            lowered = str(item).lower()
            if lowered in keys_to_symbols:
                resolved.add(keys_to_symbols[lowered])
            else:
                pf.debug(f"Unrecognized component in metadata: {item!r}")

    return resolved


def prepare(doc):
    global mode, components
    mode = str(doc.get_metadata('mode', 'layout')).lower()
    load_definitions()

    meta_components = doc.get_metadata('components', [])
    if not isinstance(meta_components, list):
        meta_components = []

    components.update(resolve_components(meta_components))
    pf.debug(f"Using mode: {mode}")
    pf.debug(f"Enabled components: {sorted(components)}")


def page_divider(label, width=60, border='='):
    label = f" {label} "
    total = width - len(label)
    left = total // 2
    right = total - left
    return border * left + label + border * right


def build_div(handler, kind, content):
    cstyle = handler.get_style(mode, kind)
    if not cstyle:
        return None
    return pf.Div(*content, attributes={'custom-style': cstyle})


def action(elem, doc):
    if not isinstance(elem, pf.Para):
        return

    text = pf.stringify(elem).strip()
    if not text:
        return

    sym = text.split()[0]

    if sym not in components:
        return pf.Null()

    handler = handlers.get(sym)
    if handler is None:
        return pf.Null()

    middle = pf.Para(*elem.content)

    if mode == 'review':
        return build_div(handler, 'wrap', [middle])

    before = build_div(handler, 'before', [pf.Para(pf.Str(page_divider(handler.key.title())))])
    after = build_div(handler, 'after', [pf.Para(pf.Str(page_divider(f'end {handler.key}')))])

    return [b for b in [before, middle, after] if b is not None]


def main(doc=None):
    return pf.run_filter(action, prepare=prepare, doc=doc)


if __name__ == "__main__":
    main()
