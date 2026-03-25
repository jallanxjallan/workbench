WORK ORDER

Purpose
Consume the output stream from `asc ingest`, buffer all payload records, require one final trailer record describing batch outcome, and reconcile that outcome against the local vault repo receipt.

This is the terminal authoring-side confirmation step of the ingest chain.
It does not modify Autoscribe state.
It records the local repo consequence of ingest success or failure.

Recommended placement
- Thin CLI entrypoint in the normal `wkb` command location:
  - cli/confirm_ingest.py
- Real implementation in the vault-boundary package:
  - vault/confirm.py
  - vault/receipts.py
- Keep write sinks separate:
  - vault/writeback.py
  - vault/writenew.py

Scope
- Input: NDJSON stream from `asc ingest`
- Output: for now, no payload output required; command may terminate silently on success
- Side effects:
  - create local confirmation tag on success
  - create local failure tag on failure
- This command runs only from inside a valid vault root / subdir and only inside a valid repo

Required dependencies
- Use the repo package for all git/repository operations
- Use existing vault discovery helpers for current registered vault root
- Use pathlib throughout
- Do not use rg_search here unless a receipt lookup helper already depends on it; receipt matching should prefer repo receipt metadata, not fresh filesystem scans

Non-goals
- Do not call `asc ingest`
- Do not re-parse source markdown
- Do not resolve slugs to paths again unless absolutely needed for a sanity check
- Do not mutate or re-emit the NDJSON payload unless a later workflow explicitly requires pass-through
- Do not write back content into vault files in this first version
- Do not create directories or repair the repo
- Do not shell out directly to git from this module

Input contract
The NDJSON stream contains:
1. zero or more ordinary payload records passed through unchanged from ingest input
2. exactly one final trailer record at end of stream

Trailer record
Use a reserved shape, for example:
- `_op: "asc.ingest.result"`

Success example
{"content":"...","input_record":{"origin":{"filepath":"/abs/a.md"},"slug":"pss.a"}}
{"content":"...","input_record":{"origin":{"filepath":"/abs/b.md"},"slug":"pss.b"}}
{"_op":"asc.ingest.result","status":"ok","batch_id":"content.topic.xyz98765","record_count":2}

Failure example
{"content":"...","input_record":{"origin":{"filepath":"/abs/a.md"},"slug":"pss.a"}}
{"content":"...","input_record":{"origin":{"filepath":"/abs/b.md"},"slug":"pss.b"}}
{"_op":"asc.ingest.result","status":"failed","error":"duplicate slug pss.foo.bar","record_count":2}

Batch semantics
- Ingest is atomic at batch level
- Either all payload records are accepted and one batch_id is assigned
- Or the whole batch fails
- confirm-ingest must never treat the stream as partially successful

Receipt-matching strategy
Match against the pre-ingest submit receipt created by `slug_to_paths`.

Canonical manifest for matching:
- ordered absolute filepaths extracted from payload records
- optionally ordered slugs if present
- same vault root / repo context

Do not rely on fresh rg_search to reconstruct the selection.
The pre-ingest submit receipt is the authority.
Filesystem/provenance data from buffered records is only the bridge used to find that receipt.

Success tag
Create an annotated tag:

- batch/<batch_id>

Tag target
- the same commit targeted by the matched submit receipt

Tag message: store
- batch_id
- confirmed_at
- submit_receipt tag name
- commit
- record_count
- ordered absolute filepaths
- ordered slugs if present in records

Failure tag
Create an annotated tag, for example:

- failed/<receipt_id>

Alternative is fine if repo package already has a preferred failed-ref convention.

Tag target
- the same commit targeted by the matched submit receipt

Tag message: store
- failed_at
- submit_receipt tag name
- commit
- record_count
- error / failure note from trailer
- ordered absolute filepaths
- ordered slugs if present

stdout
- no normal payload output required in this first version
- do not print human chatter to stdout
- if future chaining requires pass-through, add that later explicitly rather than guessing now

stderr
Allowed for brief human diagnostics only.
Keep machine-readable output off stderr for now.

Suggested helpers
In vault/confirm.py:
- read_ndjson_stream(stream) -> list[dict]
- split_payload_and_trailer(records) -> tuple[list[dict], dict]
- validate_trailer(trailer, payload_count) -> None
- extract_ordered_manifest(payload_records) -> Manifest
- confirm_ingest_result(manifest, trailer, vault_root) -> None

In vault/receipts.py:
- find_matching_submit_receipt(manifest, vault_root) -> SubmitReceipt
- create_batch_receipt(submit_receipt, trailer, manifest) -> str
- create_failed_receipt(submit_receipt, trailer, manifest) -> str

Manifest shape
A simple internal structure is fine, for example:
- ordered_filepaths: list[Path]
- ordered_slugs: list[str]   # optional, may be empty
- record_count: int

Payload extraction rules
From each ordinary payload record:
- gather `input_record.origin.filepath` if present; this is the primary bridge key
- gather `input_record.slug` if present; this is a helpful secondary identity
- preserve input order exactly

Hard-fail conditions
- no trailer record
- more than one trailer record
- trailer record not last
- trailer missing `_op == "asc.ingest.result"`
- trailer record_count does not equal number of buffered payload records
- success trailer missing batch_id
- failure trailer missing error / reason
- any payload record missing required provenance filepath
- payload manifest does not match exactly one submit receipt
- repo unavailable
- vault unavailable

Implementation notes
- Keep this as a thin reconciliation layer
- All git behavior must go through repo package
- Receipt lookup / creation logic belongs in vault/receipts.py, not inline in the CLI wrapper
- Do not mix in writeback/writenew behavior yet
- Later integration with writeback should be additive, not baked into first implementation

Pseudo-flow
1. discover current registered vault root
2. ensure repo exists for that vault via repo package
3. read entire NDJSON stream
4. split ordinary payload records from final trailer
5. validate trailer shape and payload count
6. extract ordered manifest from buffered payload records
7. locate exactly one matching submit receipt using manifest
8. if trailer status == ok:
   - create annotated batch/<batch_id> tag via repo package
9. if trailer status == failed:
   - create annotated failed/<receipt_id> tag via repo package
10. exit 0 on successful reconciliation

Failure policy
On any failure inside confirm-ingest itself:
- create no new confirmation/failure tag unless the matched receipt and intended failure action are both unambiguous
- raise with a clear message

Rationale
This command is the local authoring-side reconciler.
It consumes the final ingest outcome and records the corresponding local repo state.
It does not pollute the ingest payload, does not require selection ids to travel through Pandoc, and preserves batch-atomic semantics.