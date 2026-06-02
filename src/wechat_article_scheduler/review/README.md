# Review / Proof

`review/proof.py` implements `proof_of_publish` for semi-automatic flows (`waiting_confirmation`).

- No proof → job stays waiting; article must not be marked published.
- With proof → job `done`, article `published`, events `proof_submitted` / `job_done`.

See `docs/proof_of_publish.md`.
