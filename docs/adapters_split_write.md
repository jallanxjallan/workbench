## Split + Write Adapter Pipeline

Canonical split-then-write flow:

```bash
asc emit ... \
| w split files --pattern '^<!--\s*AS:SECTION\s*-->\s*$' --out-dir _new --digits 3 \
| w split write --base-dir "$VAULT" --mode writenew
```

Writeback flow (no split):

```bash
asc emit ... \
| w split write --base-dir "$VAULT" --mode writeback
```
