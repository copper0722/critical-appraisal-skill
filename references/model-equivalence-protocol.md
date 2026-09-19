# Small-model skill versus high-end comparator

The product target is small-model appraisal comparable to a high-end model on
the same literature. The course supplies the reasoning behind each executable
competency. Human/source adjudication evaluates correctness; the high-end model
is a comparator, not automatic truth.

Freeze source versions, assessment units, method instructions, questions,
development/held-out separation, endpoints and the equivalence decision rule
before evaluating held-out outputs. Do not change the skill using held-out
answers and continue calling that set held-out. Use separate study families.

Use three arms where feasible: small model without the skill, small model with
the skill, and a named high-end model. The same evidence/question/method budget
applies; record different decomposition, context windows and resource use.
Preserve raw requests/responses, failed turns, abstentions and evaluator identity.

## Comparison tool

`python3 scripts/compare_models.py protocol.json small.json high.json`

Protocol fields: `id`, `split` (`development`/`held_out`), `cases` with `id`,
`source_package_sha256`, `method_sha256`, `assessment_unit`, `route`, and
`questions` keyed by stable question ID. Each question supplies `allowed_answers`
and an optional positive `weight` declared before observing results.

Each run contains `protocol_id`, exact `model_id`, unique `run_id`,
`raw_output_sha256`, and `cases`. Each case repeats the identity fields and has
`status` (`complete`/`failed`/`abstained`) and `answers` keyed by question ID.
Adapters must verify raw output against the declared hash before producing this
normalized receipt. The tool records receipt hashes; it does not read remote logs
or certify their authenticity. Use controlled answers, not string comparison of
free-form narratives, for its categorical metric.

Missing cases/answers remain in the planned denominator. Failed/abstained cases
cannot contribute completed answers. Differing source/method/unit/route identities,
duplicate cases, invalid vocabularies or same-model comparisons fail closed.
The report keeps per-question differences and both paired/planned denominators.
It never declares equivalence by agreement alone. Two wrong answers can agree.

## Final acceptance still required

Evaluate source-grounded facts, judgment rationale, important omissions, invalid
clinical extrapolation, uncertainty calibration, reproducibility and correction
burden. Adjudicate discrepancies against the actual source and pinned method,
preserving the initial judgments. Review agreement cases too, to catch shared
mistakes. Report per-document-type results, not only a pooled score dominated
by easy cases. Quantify uncertainty and retain unresolved disagreements.

Any statistical equivalence/noninferiority margin, minimum coverage/sample size
and material-error exclusion rule must be justified and frozen prospectively.
No margin or sample size has yet been validated for this project; do not invent
one after seeing model results. The four synthetic cases are development tests,
not an appraisal benchmark or a basis for a universal quality claim.
