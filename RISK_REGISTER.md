# Risk Register — Team 13: Data Anonymization

Risks identified during FP2 scoping and managed through weekly instructor
reviews across the semester; formalized in register form at project close
(FP10), with each risk's final status and what actually happened.
Format per the course risk-management material: Probability × Impact on a
1–5 scale; responses are Avoid / Mitigate / Transfer / Accept.

| ID | Risk description | Category | P | I | Score | Priority | Response | Owner | Final status |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | Free-tier hosting (single instance, cold starts, spin-down) degrades or breaks weekly live demos | External | 4 | 3 | 12 | Medium | Mitigate: warm `/api/health` before every demo; local `uvicorn` fallback rehearsed | Chris | Closed — fired repeatedly (cold starts, one stale deploy, one missed auto-deploy); warm-up habit and manual deploys contained it; zero failed demos |
| R-02 | Hosting platform's edge firewall interferes with legitimate traffic | External | 2 | 4 | 8 | Medium | Accept, then Mitigate when it fired | Chris | Closed — fired: firewall blocked .sql uploads as SQL-injection attempts; fixed with base64 file-part transport; documented in SCALABILITY.md |
| R-03 | Two-person team with conflicting schedules (full-time night shift, work travel) stalls progress | Resource | 4 | 4 | 16 | High | Mitigate: strict ownership split (engine/API vs parsers/UI), async Teams communication, repo as single source of truth | Both | Closed — fired (travel week, canceled classes); split + async workflow held; no missed deliverables |
| R-04 | Scope creep: 14+ reference techniques and instructor stretch requests exceed semester capacity | Schedule | 4 | 3 | 12 | Medium | Mitigate: priority-ordered backlog in FP_iteration_plan.md; stretch items drop first; scope to 10 techniques with documented exclusions | Both | Closed — scope held at 10 techniques; preview and XLSX deliberately descoped; instructor additions (scalability, batch) absorbed using schedule slack from early deliveries |
| R-05 | Reversible mode (encryption, key handling) is unfamiliar territory and the project's hardest feature | Technical | 3 | 5 | 15 | High | Mitigate: standard primitives only (PBKDF2, Fernet — never homemade crypto); built one week early to leave correction time | Chris | Closed — delivered FP5 week; exact restore verified by automated round-trip tests |
| R-06 | Fake-value generation breaks at scale (finite name pools, collisions) | Technical | 2 | 4 | 8 | Medium | Accept initially; Mitigate when stress testing exposed it | Chris | Closed — fired at ~65k distinct values (restore refused ambiguous mappings); fixed with collision-aware generation; 65k-row round trip in CI |
| R-07 | Hand-written SQL parser fails on real-world files (comments, quoting, multi-row inserts, type declarations) | Technical | 4 | 3 | 12 | Medium | Mitigate: build against the real Assignment 2 dump; peer code review; fuzz testing with deliberately broken files | Sophie | Closed — review and fuzzing caught DECIMAL(10,2) column bug, case-sensitivity, comment handling; all fixed with tests |
| R-08 | PII detection false positives/negatives undermine trust in the tool | Technical | 4 | 2 | 8 | Medium | Mitigate: column-name-first detection, suppression rules, and a per-column user override (Keep) as the safety net | Both | Closed — fired twice (product_name as person name, 5-digit IDs as ZIPs); both fixed; Keep override shipped; documented as a heuristic with user control |
| R-09 | Divergent copies / merge conflicts corrupt the shared repo | Resource | 3 | 2 | 6 | Low | Mitigate: pull before work, small frequent commits, repo as source of truth | Both | Closed — fired (README merge conflicts committed twice, one misplaced-folder commit); all caught in review and repaired; habit of checking for conflict markers adopted |
| R-10 | Uploaded test data could contain real PII, creating the very exposure the tool exists to prevent | Security/Privacy | 2 | 5 | 10 | Medium | Avoid: fictional/generated data only (samples, Faker, AI-generated per AI_DATA_PROMPT.md); no persistence server-side — files processed in memory per request | Both | Closed — no real PII used at any point; in-memory processing verified |
| R-11 | Key file or passphrase loss makes "reversible" data permanently unrecoverable | Technical | 3 | 3 | 9 | Medium | Accept + document: by design, no key = no recovery (that is the security property); UI warns users to keep both safe | Chris | Closed — documented in UI and README; wrong-passphrase failure is clean and total |
| R-12 | Instructor-directed pivots (scalability focus, canceled sessions) disrupt the planned iteration cadence | Schedule | 3 | 3 | 9 | Medium | Accept: plan explicitly treated as not cast in stone; changes logged in FP_iteration_plan.md | Both | Closed — FP7/FP8 sessions canceled; scalability directive absorbed; changes log documents every deviation |

## Reading the register

Seven of twelve risks fired during the semester (R-01, R-02, R-03, R-06,
R-07, R-08, R-09, R-12). None became a project-level failure: each had a
response that held or was contained within its iteration. The two
highest-scored risks (R-03 schedule, R-05 reversibility) were managed by
structure — the ownership split and building the hardest feature early —
rather than by reaction, which is the register's main lesson.
