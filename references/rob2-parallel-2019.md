# RoB 2 parallel-trial proposal engine

`scripts/rob2.py` implements the decision diagrams for the **22 August 2019**
guidance, for one numerical result of an individually randomized parallel-group
trial. It accepts explicit signalling responses; it does not infer them from a
paper or certify their supporting evidence. Cluster and cross-over designs need
their separate tools and are refused here.

Authority: [official RoB 2 version page](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2).
The verified unchanged [guidance PDF](https://www.cochrane.de/sites/cochrane.de/files/uploads/RoB_2.0_guidance_2019.pdf)
has SHA256 `a9e9c4fdc4be2d29b5c0a1a6b828e09f2014a34f6d5c302a532f6153ea0fd670`.
The manual declares CC BY-NC-ND 4.0. This repository does not distribute a copy,
translated questionnaire, or modified manual. Supply the unchanged original to
the command. The algorithm code is independent decision-support software, not
an official revision or endorsement of the instrument.

## Input and execution

```sh
python3 scripts/rob2.py assessment.json --manual /path/to/original-guidance.pdf
```

The input schema is `rob2-assessment/v1`:

- `method`: `id: rob2-parallel`, `version: 2019-08-22`, the verified original
  `manual_sha256`, and `scope_verified: true` only after actual design review.
- `assessment_unit`: nonempty `study_id`, `experimental`, `comparator`, `outcome`,
  `timepoint`, `result_id`, `design: individually_randomized_parallel`, and an
  explicit `effect_of_interest: assignment` or `adhering`.
- For `adhering`, `deviation_types` selects one or more of
  `non_protocol_interventions`, `implementation_failures`,
  `participant_non_adherence`. These choices belong to the assessment protocol.
- `sources`: records with unique nonempty `id` and exact lowercase `sha256`.
- `domains`: all five keys `D1` through `D5`. Each contains `answers`, keyed by
  the original question numbers, and `support`, keyed by each answered question.
  Each support record contains a `reason`, bound `source_ids`, and a `locator`
  (or explicit searched-coverage statement for an absence judgement).
- `D2` also carries `effect_of_interest`, which must equal the assessment's
  selector. Question numbers 2.3-2.6 have different meanings across its branches;
  answers must never be reused across those branches merely because IDs match.

For example, the response record for an already source-verified D1 assessment
can have the following shape. These placeholders are not evidence:

```json
{
  "answers": {"1.1": "Y", "1.2": "Y", "1.3": "N"},
  "support": {
    "1.1": {"reason": "Explain the actual evidence", "source_ids": ["report"], "locator": "Exact location"},
    "1.2": {"reason": "Explain the actual evidence", "source_ids": ["protocol"], "locator": "Exact location"},
    "1.3": {"reason": "Explain the actual evidence", "source_ids": ["report"], "locator": "Exact location"}
  }
}
```

Use the supplied original tool to determine question wording and answer meaning.
The valid tool responses are `Y`, `PY`, `PN`, `N`, and (where offered) `NI`.
An inactive conditional question must be omitted or `NA`; an active question
cannot be `NA`. Question **3.2 does not offer NI**. The runner's technical
`NO_INFORMATION`, or a missing required response, produces `HOLD`. It never
silently becomes the tool's NI, N, zero, or a final judgement.

## Algorithm provenance and limits

| Domain | Decision authority | Preserved distinctions |
| --- | --- | --- |
| D1 | Figure 1; Tables 3-4, pp19-20 | NI differs by question; concealment differs from sequence generation |
| D2 assignment | Figure 2; Tables 5-6, pp30-33 | Deviation and analysis subproposals are evaluated separately, then combined |
| D2 adhering | Figure 3; Tables 7-8, pp36-38 | Selected deviation types; conditional questions; suitable analysis does not automatically mean Low |
| D3 | Figure 4; Tables 9-10, pp47-48 | No NI option for 3.2; no invented missing-data percentage threshold |
| D4 | Figure 5; Tables 11-12, pp56-57 | NI on 4.2 preserves at least Some concerns; later answers can still produce High |
| D5 | Figure 7; Tables 13-14, pp66-67 | One relevant NI can yield Some concerns; outcome-measurement and analysis selection stay separate |

Figure 1 covers a combination absent from Table 4: N/PN on 1.1 with Y/PY on
1.2 gives Some concerns even when 1.3 is N/PN/NI. Figure 3's inclusive branch
also covers simultaneous adverse 2.4 and 2.5 responses, not enumerated together
in Table 8. Where prose tables omit NI combinations, this implementation follows
the mapping tables and decision figures cited above. These choices require
independent source review; they are not repairs to the original manual.

Each domain returns its original response trace, source anchor and algorithm
proposal. A reviewer may provide an `override` with `judgement`, `reviewer`, and
`reason`; both the original proposal and the override remain visible. A technical
HOLD cannot be bypassed by an override. The overall result uses the reviewed
domain judgements and never falls below their highest risk level.

When several domains have Some concerns and none has High, the manual requires
a qualitative judgement about their combined effect on confidence. The engine
returns `HOLD` until `joint_concerns` contains an explicit boolean
`substantially_lowers_confidence`, a `reviewer`, and a `reason`. It has no numeric
threshold that automatically upgrades several concerns to High, and no sum score.

The assessment's source hashes, reasons and locators are preserved and structurally
checked. Their actual relationship to the proposed answers still needs source
verification: `semantic_acceptance` and `claim_use_allowed` remain false. Use the
source-binding workflow and independent discrepancy review before adopting a
report. Developer branch/identity tests do not establish model appraisal quality.

This engine supplies the MC09 decision component and supports MC02, MC07 and
MC08 traceability. Model-based signal extraction, full-report calibration and
untouched held-out trial evaluations remain separate unfinished acceptance work.
