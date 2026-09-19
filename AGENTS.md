---
summary: Portable public literature-appraisal skill and small-model tooling.
status: active
owner: repository-maintainer
---

# Critical appraisal skill

This repository owns the portable workflow, packet/draft tooling, synthetic tests
and course-to-skill traceability. Private course manuscripts and source payloads
remain with their owners. It does not own clinical, corpus or publication decisions.

- Never commit private paths, host/account configuration, credentials, patient
  data, captured papers, social-post bodies or runtime logs.
- Preserve source identity, method version and the assessment unit. A passing
  structure/quote check is not semantic correctness or human-quality evidence.
- Route by actual methods; unsupported material gets explicit limits, not an
  invented risk-of-bias label. Do not equate reporting quality with validity.
- Bind any human-quality claim to independent qualified human ratings and an
  untouched held-out evaluation. Synthetic developer keys are not human gold.
- Keep one owner per implementation; private integrations import this package
  rather than fork the portable scripts.
- Tests: python3 -m unittest discover -s scripts -p 'test_*.py'.
- Model tests require explicit local endpoint/model identity, preserve attempts,
  and never reload a model or retry an unresolved request automatically.
