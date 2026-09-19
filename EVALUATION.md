# Development evidence and limits

2026-09-19: six offline unittest methods pass, including malformed outputs,
source-hash changes, missing full text/method scope, NO_INFORMATION and budget gates.
These tests concern the draft contract, not the truth of an appraisal.

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
