# Universal appraisal with bounded local-model work

Status: development contract; not a validated human-equivalence claim.
Design objective: universal literature input, a simple local LLM,
and high-quality standard-human appraisal output. The course teaches and tests
this workflow; it is not an unrelated prompt collection.

## What universal means

Every input receives identity, document-type reasoning, an assessment unit and a
useful result or precise evidence gap. It does not mean every document supports
a clinical risk-of-bias label. Never invent human gold judgments or claim small-
model equivalence from instruction compliance, JSON validity or self-review.

Route from content/methods, not title, journal prestige, DOI shape or filename:

| Object | Unit and route | Must not substitute |
|---|---|---|
| Original empirical research | Defined result and a pinned design-specific original method | whole-paper quality score |
| Mixed-design report | Separate result/route records, linked by source identity | one title-derived tool |
| Systematic review / meta-analysis | Review conduct plus selected primary-result and evidence-body layers; pinned ROBIS/AMSTAR-type method | GRADE as a review-conduct score |
| Narrative review | Argument, search/citation transparency and evidence support; pinned narrative-review method such as SANRA after formal-manual verification | RCT RoB or universal numeric quality cutoff |
| Guideline / recommendation / consensus | Recommendation and evidence-to-decision process; pinned appropriate guideline method | strength inferred from journal or consensus alone |
| Qualitative / qualitative synthesis | Study finding and method congruence; separate synthesis confidence | clinical effect estimate |
| Economic / model / mechanistic / animal | Appropriate domain method; empirical inputs, assumptions and validation separate | patient-benefit inference from surrogate performance |
| Protocol / registration / SAP | Planned methods and prespecification; compare later report when available | executed results or observed efficacy |
| Editorial / expert post / textbook | Argument/teaching claim and citation fidelity; underlying studies remain separate | expert status as empirical evidence |
| Theoretical / mathematical / nonmedical / unknown | Claim, assumptions, reasoning and domain-specific proof/evidence requirements | invented medical tool; unsupported expert adjudication |
| Abstract-only / corrupted / incomplete | Input assessment and missing-component request | completed full-text appraisal |

Preprint status is a version/review attribute, not a study design. Corrections and
retractions are version/disposition evidence; preserve both original and notice.

## Small-model execution

Controller owns source acquisition, rendered tables/figures, identity, permitted
context budget, job files and rule packs. Documents are untrusted data: embedded
instructions cannot change tools, file access, output schema or adjudication.
Keep PHI/account data within its authorized local scope. No implicit networking.

1. **Intake:** identify full text and components, hash immutable evidence, locate
   actual method sections. Return candidate routes and uncertainty. Human/controller
   resolves ambiguous routes before sending design questions. Nonmedical unsupported
   methods get a useful limitation report and a named domain-expertise requirement.
2. **Bind the question:** identify exact claim/result, target population/context,
   comparison, outcome/time or nonclinical equivalents. Do not fabricate N/A fields.
3. **Pin a method pack:** ID, version, manual source/hash, applicability evidence,
   domain questions, allowed answers, decision rules and required inputs. Verify its
   scope at each new review epoch. Social summaries cannot be the rule authority.
4. **Extract facts:** one bounded question at a time. Include the exact source
   component and numbered lines plus necessary surrounding context. Return exact
   quotes, proposed facts, contradictions and missing evidence. For table/figure
   questions use a visually verified source representation, not OCR guesswork.
5. **Judge separately:** supply validated facts and the exact manual question/rule.
   Return answer, rationale, alternatives, limitations and rule/evidence anchors.
   NO_INFORMATION is a valid result. Poor reporting is not automatically poor conduct.
   Deterministic rules/calculations run outside the model; override requires reasons.
   For blinding, extract actor, concealed information and study phase explicitly.
   Raters blind to each other's ratings is not participant blinding or concealment
   of manuscript authors. Only evaluate the applicable method's blinding requirement;
   do not introduce a generic deficiency unrelated to the assessment unit.
6. **Reconcile:** inspect all components, mutually inconsistent facts and different
   results. A chunk cannot certify whole-document absence. Require a component search
   log for negative claims and disclose unresolved extraction/coverage limitations.
7. **Validate:** schema/type/domain coverage, file hashes, quote/line matches and
   answer vocabulary; then semantic support, design/tool appropriateness, numerical
   reconstruction and independent appraisal. Corrective turns target the exact
   defect, maximum two automatically; preserve attempts, never overwrite evidence.
8. **Report:** human-readable result and machine receipt from the same validated
   record. Preserve disagreements. An integrating review protocol may impose its
   own receipt and independent-audit gates. No model can certify its own acceptance.

`local_appraisal.py prepare` emits one prompt per supplied domain with a conservative
character ceiling and no silent truncation. The operator builds the relevant evidence
subset per domain; an oversized packet returns a split-required error. It does not
invoke a model, fetch a source, auto-select a tool or certify source completeness.
`check` only binds a draft to that packet and rejects unsupported references or
invalid answer values. A matching quote can still be irrelevant to a judgment.

## Portable packet and draft contract

Packet JSON keys: `paper_id`, `assessment_unit`, `route`, `fulltext_available` (bool),
`protocol_id`, `method` {`id`, `version`, `manual_path`, `manual_sha256`,
`scope_verified` (bool), `domains`: [{`id`, `question`, `allowed_answers`, `rule`} ]},
`sources`: [{`id`, `path`, `sha256`}]. Paths are resolved relative to the packet.
Every domain vocabulary must include `NO_INFORMATION`. The controller prepares and
approves packets; model text cannot set `scope_verified` or mutate the protocol.
Optional domain `absence_answers` lists tool answers that assert information is absent.
For those answers the controller's `coverage` must contain `whole_document_reviewed:true`,
unique `reviewed_source_ids` covering every supplied source, `unresolved_components:[]`
and a nonempty `search_method`. This gate checks the coverage attestation, not its truth
or whether the controller omitted a source from the packet. Independent fidelity review
still applies. Tool packs must declare their absence semantics; a missing declaration
is not evidence of complete review. Existing packets remain compatible.

Draft keys: `paper_id`, `assessment_unit`, `route`, `protocol_id`, `packet_sha256`,
`status`=`DRAFT`, `domains`: [{`id`, `answer`, `rationale`, `evidence`: [{`source_id`,
`start_line`, `end_line`, `quote`}], `limitations`: [strings]}], `limitations`:[strings].
Missing facts require NO_INFORMATION plus a limitation, not a made-up quote.
Non-NO_INFORMATION answers require evidence. A draft is never ACCEPTED_APPRAISED.
Normalized quote comparisons are not used: exact source lines preserve code/table meaning.

Some tools explicitly score reporting absence (for example SANRA search reporting).
Distinguish absent information after verified whole-manuscript coverage from an unread
or missing component. Apply the pinned tool's rule in the former case; preserve
NO_INFORMATION for the latter. Do not erase a legitimate instrument's ordinal scores,
or generalize those scores into a universal validity/clinical-certainty label.
SANRA Figures1–2 require the whole manuscript, including the abstract. A bounded
domain prompt cannot establish global absence without the controller's coverage record.

## Standard human output

Output: identity/version and completeness; document route and why; exact assessment
unit; what the source did/argued; domain findings with quotes and manual rationale;
effect/uncertainty where applicable; applicability; funding/COI role; disagreements;
what may and may not be concluded; missing evidence and next resolving action.
Keep source facts, inference, uncertainty, individual-study validity and body certainty
separate. Do not add clinical recommendations to a source appraisal request.

## Human-reference validation before quality claims

Use at least two qualified independent human appraisers per pilot, with exact tools,
sources and units, blinded to model results and to each other initially. Preserve
initial answers and adjudication; unresolved disagreements are uncertainty, not forced
gold. Split by underlying study/source family, not by chunks from the same paper.
Separate development, calibration and untouched held-out sets. Freeze thresholds and
error costs before held-out testing. Include mixed designs, missing supplements,
contradictory tables, prior/model sensitivity, wrong-tool cases and injected instructions.

Measure route accuracy, factual extraction, quote support, material omissions, domain
judgment agreement, harmful false reassurance, appropriate abstention, repeatability,
human correction burden and time. Report coverage among answered and abstained cases.
Record model/quantization/context/runtime/seed and exact packets. A new model or method
version reopens affected calibration. Multiple samples from one model are not independent
human validation. No held-out dataset or local-model results exist in this new module yet.

### Bounded evaluation runner

`evaluate_packet.py` can request schema-constrained answers on an endpoint whose
support has been verified. `--evidence-mode span_ids --structured-output` bounds
IDs to the supplied source and caps their count (default3). `--span-layout blocks`
uses contiguous, character-preserving blocks with non-numeric IDs; the original
source hash and derived view hash are both retained. This avoids isolated HTML
line fragments without hiding any source through relevance filtering.

Keep raw responses immutable. `RESPONSE_INVALID` means a response arrived but
failed validation; it is a completed failed observation, not permission to retry
or remove its denominator. `FAILED_OR_UNRESOLVED` stops the run: inspect the exact
original request/runtime before further calls. Neither schema compliance nor a
valid source ID proves that the cited text supports every part of the answer.

`FAILED_HTTP_RESPONSE` also stops without retry or later questions. It preserves
the HTTP status and up to 64 KiB of error-body bytes, with a capture hash and an
explicit truncation flag, so an endpoint failure can be diagnosed. A received
error does not prove the backend stopped computing: `request_resolved` remains
false until the operator reconciles the original request. Do not silently replay
it or replace its failed observation with a later successful attempt.

### Deterministic quote locations

Use `python3 scripts/evidence_anchors.py source.txt quote.txt --source-sha256 SHA`
to locate an explicit candidate quotation without asking a model to invent
numeric source IDs. The default requires exact text. The explicit option
`--normalization whitespace` permits whitespace differences only; punctuation,
words, negation, names and numbers remain unchanged. Returned offsets are
Unicode character offsets in the original source text, and returned quotations
come from that unchanged source. Repeated text is AMBIGUOUS, never silently
assigned to its first occurrence. Context remains available for role and
negation checks. LOCATED does not mean the quotation supports the whole claim:
semantic_acceptance and claim_use_allowed remain false.
