import panflute as pf
from pathlib import Path
from typing import Optional, Dict, List
import attr
import sys


@attr.define
class SymbolSpec:
    symbol: str
    key: str


class SubmitSymbolRegistry:
    _registry: Dict[str, SymbolSpec] = {
        '¶': SymbolSpec(symbol='¶', key='running'),
        '🖼️': SymbolSpec(symbol='🖼️', key='caption'),
        '⧉': SymbolSpec(symbol='⧉', key='boxout'),
        '▌': SymbolSpec(symbol='▌', key='sidebar'),
        '❝': SymbolSpec(symbol='❝', key='pull_quote'),  # open quote only
        '⬖': SymbolSpec(symbol='⬖', key='standalone_page'),
        '📐': SymbolSpec(symbol='📐', key='layout_note'),
        '⌘': SymbolSpec(symbol='⌘', key='page_title'),
        '📖': SymbolSpec(symbol='📖', key='pdf_page'),
    }

    @classmethod
    def get(cls, symbol: str) -> SymbolSpec:
        if symbol not in cls._registry:
            raise ValueError(f"Unrecognized symbol prefix: {symbol!r}")
        return cls._registry[symbol]

    @classmethod
    def all_symbols(cls) -> List[str]:
        return list(cls._registry.keys())


@attr.define
class BaseFilter:
    components: List[str] = attr.field(factory=SubmitSymbolRegistry.all_symbols)
    errors: List[str] = attr.field(factory=list)

    def error(self, message: str):
        self.errors.append(message)

    def finalize(self, doc):
        if not self.errors:
            return

        RED, RESET = "\033[91m", "\033[0m"
        print(f"\n{RED}Errors encountered during filter execution:{RESET}\n", file=sys.stderr)
        for err in self.errors:
            print(f"{RED}  • {err}{RESET}", file=sys.stderr)

        with open("filter_errors.log", "w", encoding="utf-8") as f:
            for err in self.errors:
                f.write(f"- {err}\n")

        sys.exit(1)

    def parse_paragraph_symbol(self, para: pf.Para) -> str:
        text = pf.stringify(para).strip()
        if not text:
            self.error("Blank paragraph encountered.")
            return ""
        symbol = text[0]
        if symbol not in SubmitSymbolRegistry.all_symbols():
            self.error(f"Paragraph does not begin with a recognized symbol: {text!r}")
            return ""
        return symbol


class CombinedFilter(BaseFilter):
    def action(self, elem, doc):
        if isinstance(elem, pf.Para):
            symbol = self.parse_paragraph_symbol(elem)

            if not symbol or symbol not in self.components:
                return pf.Null()

            # Copy inlines and drop the first character (the symbol)
            inlines = list(elem.content)
            if inlines and isinstance(inlines[0], pf.Str):
                inlines[0].text = inlines[0].text[1:].lstrip()
                if not inlines[0].text:
                    inlines.pop(0)

            return pf.Para(*inlines)

        return None



def main(doc=None):
    filt = CombinedFilter()
    pf.run_filter(filt.action, finalize=filt.finalize, doc=doc)


if __name__ == "__main__":
    main()
