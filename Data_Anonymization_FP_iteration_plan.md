# FP Iteration Plan — Team 13: Data Anonymization
**SKELETON DRAFT** — owners and details to be assigned at the FP2 meeting. Iteration numbers/dates to be aligned with the course calendar. This plan is not cast in stone; it will be reviewed and adjusted in weekly breakout sessions.

**Team:** Chris Nhul, Sophie Tony-Uduhirinwa
**Repo:** github.com/nhulchris/data_anonymizer
**Presentations:** Nov 24 (Batch 1) / Dec 1 (Batch 2)

| Iteration | Week of | Focus | Planned deliverables / demo | Owner |
|---|---|---|---|---|
| FP2 | Sep 22 | Scope, plan, research | Agreed scope; this plan committed; AI review of Assignment 2 code (prioritized fix list); market research on existing tools (Presidio, ARX, Faker, Gretel); risk register v1; stack feasibility spike (client-side processing) | TBD |
| FP3 | Sep 29 | Foundation | Stack finalized; project skeleton deployed (hello-world on Vercel); engine scaffold + CSV parser; first technique working end-to-end (substitution) — demo: upload CSV, download anonymized CSV | TBD |
| FP4 | Oct 6 | Core techniques I | Pseudonymization with consistent mapping; nulling; partial masking; unit test suite established (TDD); basic UI: upload → column list → download | TBD |
| FP5 | Oct 13 | Core techniques II + SQL | Hashing; generalization; SQL parser integrated (port from A2); per-column technique selection in UI with preview | TBD |
| FP6 | Oct 20 | Flagship: reversibility | Reversible mode — encrypted mapping/key file, restore verified exact; cross-table consistency demo on multi-table SQL dump | TBD |
| FP7 | Oct 27 | Flagship: FPE + JSON | Format-preserving masking (card numbers, phones); JSON support; malformed-input handling + fuzz tests | TBD |
| FP8 | Nov 3 | Polish + stretch | UI polish; documentation (README, DESIGN.md); stretch items only if core is green (shuffling, perturbation, synthetic, XLSX) | TBD |
| FP9 | Nov 10 | Freeze + evidence | Feature freeze; regression pass; testing-evidence writeup; sample original + anonymized datasets in repo; presentation draft | TBD |
| FP10 | Nov 17 | Working session | Bug fixes only; presentation rehearsal; self-evaluation spreadsheet drafted (Done / Partially Done / Not Done vs. this plan) | TBD |
| Final | Nov 24 / Dec 1 | Presentation + handoff | Final presentation; final weekly signoff; confirm GitHub origin has latest code; submit self-evaluation | Both |

## Working agreements (proposed — confirm at FP2 meeting)
- Communication: Microsoft Teams
- Weekly signoff: each member submits individually by class-day midnight, newest entry on top
- Every iteration ends with something demoable in the breakout room
- Scope is the adjustment lever: if an iteration slips, stretch items drop first, then FP8 polish — flagship and core items are protected
- Each risk in the risk register has a named owner; register reviewed briefly each week

## Backlog priority order (for scope adjustment)
1. Core techniques on CSV + SQL (must ship)
2. Reversible mode (must ship — it is the project's headline requirement)
3. JSON support
4. Format-preserving masking
5. UI preview/polish
6. Stretch items (first to drop)
