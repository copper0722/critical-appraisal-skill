# Development evidence and limits

2026-09-19: six offline unittest methods pass, including malformed outputs,
source-hash changes, missing full text/method scope, NO_INFORMATION and budget gates.
These tests concern the draft contract, not the truth of an appraisal.

The expanded suite has14 test methods: it also checks absence-versus-unknown
coverage, paired comparison identity, missing/failed/abstained denominators,
same-model refusal and finite positive weights. These are infrastructure tests.
At that checkpoint no high-end paired output was recorded; the development comparison
below is now available. No held-out equivalence result exists.
The objective is small-plus-skill versus high-end quality; human/source review
adjudicates correctness rather than declaring the high-end model infallible.

An existing local mlx-community/Qwen3-VL-8B-Instruct-4bit service was tested without
reloading. In a short methods-paraphrase pilot it selected instrument evaluation,
but introduced an unsupported blinding concern. It was not a full-text appraisal.

Four original synthetic development cases then tested blinding actors and
within-report versus cited-study randomization. Joint prompting passed1/4 under
strict string scoring. One failure included harmless grammatical variations;
two involved substantive actor/report confusion. Do not interpret1/4 as a pure
semantic accuracy measure.

Factwise prompting with controlled answer vocabularies and exact supporting
quotes passed3/4 on the same development cases. The remaining failure reported
NOT_REPORTED instead of NO despite an explicit statement that the review authors
did not allocate participants. The comparison also changed answer format, so it
does not isolate the causal effect of decomposition alone. It is not held-out.

The next gate is out-of-sample source-bound evaluation, preserving abstentions,
wrong roles, citation confusion, contradictions and corrected attempts. Human-grade
claims require independent qualified human judgments and adjudication, not model
self-review, synthetic keys or these preliminary counts. No such claim is made.
## Paired synthetic development comparison

The local8B factwise output was compared to a separately invoked native
gpt-6-astra/high comparator, which received the same four synthetic sources,
field questions and allowed vocabularies, without reference answers or prior
small-model outputs. The small model used one request per field; the comparator
received the fields in one bounded request. This is a workflow comparison, not
a controlled test of model capacity under identical call decomposition.

All16 fields paired;15 categorical agreements. Five agreements are NOT_REPORTED
on intentionally missing information. On the11 reference-answerable fields,
10 agree. The remaining review-of-trials allocation answer was NOT_REPORTED for
the small model and NO for the comparator; the source explicitly states the
review authors did not allocate participants. This supports NO for that fixture.
No full-document appraisal or universal-equivalence conclusion follows.

An initial controller packet-generation SyntaxError was accidentally sent instead
of the cases; the comparator returned an empty case list. That is an input-pipeline
failure, not model-performance evidence. The corrected packet was JSON-validated
and checked for4 cases/4 fields before one corrected submission. The reusable
exporter now tests those invariants and excludes reference answers. The native
model snapshot was not exposed beyond the selected model identifier.

Current offline suite:20 test methods, adding source-read SANRA scope, six-item
score handling, whole-document coverage and comparator input export. Passing
these tests still does not establish semantic appraisal quality.
