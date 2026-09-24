# Worker schema and access boundaries

Read ONLY this file, protocol.md, assigned input batch, and own assigned output directory; root policy files may be read as required. Do not inspect other role outputs, old extractions, reference labels (extractor), or candidate extractions (reference author). No network/API/subagents unless coordinator explicitly delegates them.

Input papers contain paper_id/domain/title/abstract/hash/stratum. Every paper must occur exactly once in your output, including no-relation papers with records=[] and explanatory note. Output JSON is an array of paper objects. Author semantic judgments directly from the abstract; never use Python heuristics to extract or judge scientific relationships. Code may serialize author-provided records and validate quotes/IDs.

Paper object: {"paper_id":"P...","article_role":"research|review|other|uncertain","records":[...],"note":"short source-only scope/ambiguity note"}.

Record required keys:

```
{"id":"r01", "subject":"source-faithful short phrase", "subject_role":"material_entity", "predicate":"source-faithful directed relation", "object":"source-faithful short phrase", "object_role":"quantity", "quote":"EXACT contiguous source substring; may contain multiple sentences", "assertion":"author_claim|association|hypothesis|negated", "modality":"experimental|computational|theoretical|mixed|unspecified", "conditions":"necessary material/comparison/temperature/etc qualifiers, or empty string", "joint_factors":[], "scope":"one allowed full scope name", "status":"accepted|uncertain", "note":"optional brief reason"}
```

Optional context_quotes: list of exact source substrings to disambiguate antecedents/conditions. Do not paste fabricated normalized text into quote. Entity labels and predicate may be faithful paraphrases. Keep author terminology/abbreviations where physical interpretation is uncertain.

Within a paper IDs r01 etc are unique; initial IDs persist in reviewed even when revised. New IDs must never reuse initial ones. Deleted initial rows appear only in change log; no tombstones in reviewed records. Reference uses independent g01 etc IDs.

For an extraction assignment, write own output dir `initial_raw.json`; run `python3 materialize.py <yourdir>/initial_raw.json <yourdir>/initial.json` to verify and freeze it BEFORE review. Then write `reviewed_raw.json` plus `changes.json` (paper_id, id, action=accept|revise|add|delete|uncertain, reason). Run materialize for reviewed. Freeze cannot be overwritten. Technical corrections to raw quotes are permitted before successful freeze; after freeze do not mutate records. Same one-round review may consider errors and omissions together.

For a reference assignment, write own dir `reference_raw.json`, using records as all scope-defined claims directly supported by original text. `status=uncertain` for real source ambiguity. Run materialize to `reference.json`, once. No extraction comparison or iterative refinement using other outputs.

If batch too large, author smaller blocks and concatenate only own blocks, preserving all paper coverage. No count quota for relationships and no skipping papers. Return path, paper/record counts, own isolated-context compliance, and unresolved source ambiguities. Do not report semantic accuracy from self-judgment.
