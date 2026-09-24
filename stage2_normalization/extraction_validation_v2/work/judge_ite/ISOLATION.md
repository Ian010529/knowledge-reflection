# iTE head evaluator declaration

Assigned and completed blind/iTE.json indices 0:20: 20 papers, 139 candidates, 111 references. Final artifact: judgments_head.json. judgments.json is the same authored working artifact for these 20 papers; author.py serializes explicitly authored judgments, with no similarity scoring or automatic semantic rules.

Read only judge_instructions.md, protocol.md, the assigned blind/iTE.json, and own work/judge_ite directory. Did not read private/, extraction/reference author outputs, version mapping, previous scores, other evaluators or external sources. No network/API calls and no subagents. Read restrictions were protocol isolation, not an OS sandbox. The task packet did not expose candidate versions; no versions were inferred or scored.

All candidate and reference judgments were individually authored against full abstracts. Python only displayed the packet, serialized authored statements and validated exact ID coverage/counts and coverage-set membership. Validation passed for all 20 papers. The other 10 papers were not evaluated after coordinator reduced assignment; no other evaluator output was read.

Material issues: several abstracts report findings and numbers without identifying experimental/computational methods; experimental modality assertions were treated strictly as partial candidates and uncertain references. Specific method reports, actual preparation/operation reports and experimental validation were used when present. Invalid references do not have full_coverage_sets. Review topic lists and one isolated device measurement relation were marked out_of_scope. Reference omissions are noted without denominator expansion.
