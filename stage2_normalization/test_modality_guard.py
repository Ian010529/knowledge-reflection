"""Technical regressions on source excerpts; not an extraction quality score."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from modality_guard import guard, main


class ModalityGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.papers = json.loads((Path(__file__).parent / "extraction_validation_v2"
                                 / "input_papers.json").read_text())

    def run_case(self, pid="P1415", **fields):
        record = dict(id="r1", subject="A", predicate="affects", object="B",
                      conditions="reported conditions", quote="unchanged relation quote")
        record.update(fields)
        raw = [dict(paper_id=pid, records=[record])]
        before = copy.deepcopy(raw)
        output, audit = guard(self.papers, raw)
        self.assertEqual(raw, before)
        actual = output[0]["records"][0]
        omit = {"modality", "modality_evidence"}
        self.assertEqual({k: v for k, v in actual.items() if k not in omit},
                         {k: v for k, v in record.items() if k not in omit})
        return actual, audit

    def test_default_and_missing_support_preserve_relation(self):
        for fields in ({}, {"modality": None}, {"modality": ""},
                       {"modality": "experimental"}):
            with self.subTest(fields=fields):
                record, audit = self.run_case(**fields)
                self.assertEqual(record["modality"], "unspecified")
                self.assertEqual(len(audit), 1)

    def test_explicit_source_quotes_retained(self):
        cases = [
            ("P0230", "experimental", "The mixed potential theory, zero-resistance ammeter and weight loss measurements were performed."),
            ("P0301", "theoretical", "Based on the performance of a single TREC, the power output and efficiency of the system are analytically derived."),
            ("P1803", "computational", "With the anisotropic speed of sound and intrinsic material properties as input parameters, we can predict the direction-dependent kappa(L)(theta,phi)."),
        ]
        for pid, modality, quote in cases:
            with self.subTest(modality=modality):
                record, audit = self.run_case(pid, modality=modality, modality_evidence=[quote])
                self.assertEqual(record["modality"], modality)
                self.assertEqual(audit, [])

    def test_wrong_paper_quote_downgraded_and_logged(self):
        quote = "The mixed potential theory, zero-resistance ammeter and weight loss measurements were performed."
        record, audit = self.run_case(modality="experimental", modality_evidence=[quote])
        self.assertEqual(record["modality"], "unspecified")
        self.assertEqual(audit[0]["proposed_modality_evidence"], [quote])
        self.assertEqual(audit[0]["reason"], "evidence_not_in_this_abstract")

    def test_mixed_also_requires_evidence(self):
        record, _ = self.run_case(modality="mixed")
        self.assertEqual(record["modality"], "unspecified")

    def test_malformed_fields_fail(self):
        for fields in ({"modality": "guessed"}, {"modality_evidence": "text"},
                       {"modality_evidence": [""]}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.run_case(**fields)

    def test_unknown_paper_fails(self):
        with self.assertRaises(ValueError):
            self.run_case("not-a-paper")

    def test_cli_output_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            source, raw, out = [Path(folder) / name for name in ("source.json", "raw.json", "out.json")]
            source.write_text(json.dumps(self.papers))
            raw.write_text(json.dumps([dict(paper_id="P1415", records=[dict(id="r1", modality="experimental")])]))
            main(source, raw, out)
            self.assertEqual(json.loads(out.read_text())[0]["records"][0]["modality"], "unspecified")
            self.assertEqual(len(json.loads(Path(str(out) + ".audit.json").read_text())), 1)
            with self.assertRaises(FileExistsError):
                main(source, raw, out)


if __name__ == "__main__":
    unittest.main()
