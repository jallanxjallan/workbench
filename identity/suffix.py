from __future__ import annotations

import secrets
import string


DEFAULT_SUFFIX_LENGTH = 5
_SUFFIX_LEADING_ALPHABET = string.digits
_SUFFIX_BODY_ALPHABET = string.ascii_lowercase + string.digits


class IdentityError(ValueError):
    pass


def generate_slug_suffix(length: int = DEFAULT_SUFFIX_LENGTH) -> str:
    if length <= 0:
        raise IdentityError("Suffix length must be positive.")
    if length < 2:
        raise IdentityError("Suffix length must be at least 2 characters.")

    leading = secrets.choice(_SUFFIX_LEADING_ALPHABET)
    body = "".join(secrets.choice(_SUFFIX_BODY_ALPHABET) for _ in range(length - 1))
    return leading + body


def validate_slug_suffix(value: str, length: int = DEFAULT_SUFFIX_LENGTH) -> str:
    normalized = str(value).strip()
    if len(normalized) != length:
        raise IdentityError(f"Suffix must be exactly {length} characters.")
    if not normalized[0].isdigit():
        raise IdentityError("Suffix must start with a digit.")
    if any(char not in _SUFFIX_BODY_ALPHABET for char in normalized[1:]):
        raise IdentityError(
            "Suffix must contain only lowercase letters and digits after the first character."
        )
    return normalized


"""Exactly. That is the strongest argument for doing it.

If suffix length is semantic, then a reader can infer something at a glance without needing another field:

* **short** = human-made, manually curated, low-volume
* **long** = machine-minted, imported, corpus-scale, collision-resistant

That is genuinely useful. It turns the slug from pure baggage into a tiny bit of metadata.

I’d just keep two guardrails in place.

First, let the meaning be **coarse**, not fussy.
Good:

* 5 chars = human
* 8 chars = machine

Bad:

* 5 = handwritten
* 6 = manually imported
* 7 = semi-automatic
* 8 = scraped
* 9 = RAG
* 10 = PDF chunk

Once length starts carrying too many meanings, it becomes clever in the bad way.

Second, make the semantic meaning **align with generation policy**, not with content meaning.
That is, length should answer:

**How was this minted, and what collision budget does it need?**

—not:

**What kind of intellectual object is this?**

You already have prefixes for the latter. Length works best as a signal of **provenance / volume class**.

So a clean model would be:

* `pss.project-hint.ab12c` → human-authored passage
* `spc.project-hint.q9m4t` → human-authored instruction
* `rag.project-hint.k3d9m2qx` → machine-minted corpus chunk
* `web.project-hint.7x2p4mqa` → imported/scraped object

In that scheme:

* **prefix** says what sort of thing it is
* **hint** says roughly what it’s about
* **length of identity** says how it came into being / what scale it belongs to

That is elegant.

The only caution is future regret. If one day you want human-created files in a high-volume domain, or machine-created files that should look friendly, length semantics can become a constraint. So I’d document it as:

> Identity length indicates minting class by default, not an inviolable truth about the object.

That gives you room to bend later without “breaking the theology.”

So yes — I think that is a sound design principle, and probably better than one universal identity length for your system.
"""
