import panflute as pf
from pathlib import Path
from typing import Optional, Dict, List
import attr
import sys


symbol_refs = {
    '¶': e'running_text'),
        '🖼️': 'caption'),
        '⧉': 'boxout'),
        '▌': 'sidebar'),
        '⬖': standalone_page'),
        '📐': 'layout_note'),
        '⌘': 'page_title'),
        '📖': 'pdf_page'),
}


def prepare(doc):
    meta = doc.metadata 
    doc.valid_components = {k:v for k,v in  if k in symbol_refs.items() if k in meta['components']}

def action(self, elem, doc):
    if isinstance(elem, pf.Para):
        inlines = list(elem.content)
        symbol = inlines.pop(0)

        if not symbol or symbol not in self.valid_components:
            return pf.Null()

        custom_style = 

        div = pf.Div(attr=self.valid_components[symbol] )

        return div, pf.Para(*inlines)
        

def main(doc=None):
   
    pf.run_filter(action, prepare=prepare, doc=doc)


if __name__ == "__main__":
    main()
