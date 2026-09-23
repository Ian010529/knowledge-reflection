# Corrected corpus policy

- Default inputs: `data/ite_clean.csv` (1,644 papers) and `data/tg_clean.csv` (333 papers).
- Run `python3 verify.py` before analysis.
- Retain ALL papers in the TG source collection. Remove shared papers ONLY from iTE.
- Deduplicate identities within iTE, preserving source records and abstracts. Do not discard unique papers.
- Do not use keywords, scope labels, missing abstracts, review status, solid-state labels, or hybrid mechanisms to filter this default corpus. Any future content filtering requires explicit user instruction and a separately reviewable output.
- The former 242/139 export is retracted. Never restore its default policy or use its counts as the full corpus.
- `audit/` preserves original records and identity mappings. Do not load it recursively as additional training samples.
- Old material/mechanism fields are source annotations, not independently verified observed evidence.
- Report exactly which inputs were used. Historical analysis outputs have not been recomputed for this corpus.
