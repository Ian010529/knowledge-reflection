# TG extractor isolation declaration

Agent task: /root/extract_tg_v2.

I read only the assigned TG input, protocol.md, schema.md, materialize.py, and my own work/extract_tg files. The coordinator-authorized materializer accesses input_papers.json internally for exact quote validation and metadata; I did not inspect that file or other roles. I did not inspect earlier extractions, reference labels, baseline scores, parent conversation, or other worker directories. No network, paid API, or further agent was used.

All 30 initial extractions were authored directly from full abstracts, then serialized and frozen before review. Exactly one focused review checked errors and reread all 30 complete abstracts for omissions; reviewed output was then frozen. Subsequent checks were technical integrity checks only. Python serialized explicit authored semantic records and verified structure, source spans, hashes and IDs; it did not perform heuristic semantic extraction or judgment.

The isolation is a protocol commitment, not an operating-system access restriction. No semantic accuracy estimate is self-assigned.

Unresolved source ambiguity: P0121 contains a missing starting power value and malformed Cu/Cu-2 notation; relevant records retain uncertain status without reconstructing source values. P0256 contains damaged mathematical symbols; the equation was not reconstructed. P0330 has source spelling/OCR damage, quoted verbatim; labels use the clearly identified casing context.
