## Split + Write Adapter Pipeline

Canonical split-then-write flow:

```bash
asc emit ... \
| split-files --pattern '^<!--\s*AS:SECTION\s*-->\s*$' --out-dir _new --digits 3 \
| write-vault-files --base-dir "$VAULT" --mode writenew
```

Writeback flow (no split):

```bash
asc emit ... \
| write-vault-files --base-dir "$VAULT" --mode writeback
```
