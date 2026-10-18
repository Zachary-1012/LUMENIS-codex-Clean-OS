# Complete LUMENIS candidate repository and review evidence

Open `source/` as the repository root. It contains the complete 3,315-file candidate, in the existing repository layout; no patch assembly is required. This candidate is NOT_INTEGRATED and not ready for merge/release. The full current-main patch is optional review/apply evidence, not a prerequisite for using the source tree.

- `candidate-source-manifest.json`: SHA-256 of every source file.
- `VERIFY_SOURCE.py`: independent exact-byte inventory verification (Python standard library only).
- `REPORT.md` / `FINAL_RECEIPT.json`: final same-version result and blockers.
- `PR_BODY.md`: draft PR description; explicit failed checks and missing inputs.
- `MAIN_TO_FULL_CANDIDATE.patch`: one direct patch from the official main tree; independently applied and rehashed.
- `PATCH_APPLICATION.json` / `CHANGED_FILES.json`: eight-stage pre/postimage proof and 22 distinct changes relative to the earlier candidate.
- `CANDIDATE_DISPOSITION.json` / `review-only/`: approved planning, incomplete excluded changes and local-source gaps. These are not extra patches to assemble and are not automatically publishable.
- `results/` / `evidence/`: same-version logs plus preserved prior failures, including the earlier exit139.

The existing app/ and website/ source is retained unchanged from the earlier candidate. New paused frontend patches, incomplete semantic/BYOK work and absent local dirty bytes are not in source/. Recording collection is outside this candidate; original media and speech capabilities remain.

## Replay boundary

No venv, installed dependency bundle, runtime database, private .env, credentials, user original material, reference videos or nested old ZIP is distributed. `.env.example` is the official tracked documentation template. Python/vendor and frontend package manifests remain intact.

Validation uses the existing Python 3.12 environment and installed FFmpeg/ffprobe, isolated synthetic databases and bounded public validation inputs. Source identity is independent of environment availability. Before replay, make a new disposable copy, set the validation root in env.sh to that copy, select the already available compatible Python executable, and update the one external-browser-test path in selectors.txt to that copied root. Do not replay writes in a frozen evidence directory. No package installation, external model/API, sampling, training, production DB or deployment is implied.

Only source/ defines the prospective product PR tree. Do not bulk-commit this whole backup, review-only private reports, validation inputs or runtime evidence to GitHub. Required checks and substantive review remain blocking. Missing local source bytes cannot be reconstructed from their hash list.
