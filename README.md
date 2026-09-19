# Critical Appraisal Skill

An executable companion to a critical-appraisal course: route a document,
reconstruct its evidence, apply a pinned method and return an auditable draft.
The target is reliable appraisal with small local models. **That quality target
has not yet been established by independent human-reference evaluation.**

## Available now

- A universal intake and method-selection workflow.
- Offline per-domain prompt preparation and source-bound draft checks.
- Tests rejecting altered sources, fabricated quotations and invalid drafts.
- A local-model development probe with preserved requests and responses.
- A24-unit course-to-skill map with explicit implemented/pending boundaries.

Requires Python3.10+; runtime tooling uses the standard library. Put the folder
where your agent discovers skills, or read `SKILL.md` and invoke scripts directly.

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/local_appraisal.py --help
```

Packet and draft fields are documented in
[the workflow](references/universal-local-workflow.md). Supply your own lawful
full text and original method instructions. This repository contains no papers,
private course manuscripts, provider credentials or automatic corpus integration.

## What remains

Verified method packs across document types, full-document coverage handling,
semantic adjudication, numerical checks, a complete human-readable report path,
and independent human-reference evaluation are unfinished. The framework accepts
arbitrary document routing; it does not yet automate high-quality appraisal of
every literature type. See [evaluation evidence](EVALUATION.md).

Course manuscripts remain private; the public mapping explains which competency
each executable step must implement. Source papers/manuals retain their own licenses.
No license to redistribute those sources is provided by this repository.
