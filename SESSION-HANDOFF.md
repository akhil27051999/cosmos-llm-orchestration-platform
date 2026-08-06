# SESSION HANDOFF — Nataraja (read this first next session)

> **Purpose.** Continue the work without losing context. This file is the source of truth for *where we
> are and how to continue*. Pair it with `CLAUDE.md` (rules/persona) and `LEARNING-PLAN.md` (the plan).

## 1. Project identity
- **Name:** **Nataraja — Cloud-Native LLM Orchestration Platform** (was "Flask-REST-API", briefly "Helios").
- **GitHub repo:** `akhil27051999/nataraja-llm-orchestration-platform` (renamed; GitHub redirects old URLs).
- **Local folder (unchanged by the rename):** `~/Desktop/Flask-REST-API` ← this is the working dir.
- **Branches:** `main` and `dev` — kept **identical** and pushed together every commit.
- **Theme:** Nataraja / Shiva — ring-of-fire + cosmic-violet, flame/ember accents, 🔱. Favicons: notes 📓, roadmap 🔱, architecture 🔱, study-guide 📘.

## 2. THE HARD RULE (never break)
The user **writes 100% of the implementation code themselves.** My role: teach concepts, design in prose
(no code snippets as deliverables), review what they build, produce study material. See `CLAUDE.md`.

## 3. What exists in the repo (`docs/` + root)
**Planning docs (root):** `CLAUDE.md`, `LEARNING-PLAN.md` (56-week schedule), `MASTER-BUILD-PROGRAM.md`,
`DEVOPS-CALIBRATION.md`, `CLOUD-ARCHITECT-PLAN.md`, `SCALING-ROADMAP.md`, `COVERAGE.md`,
`ARCHITECTURE-STUDY-GUIDE.md` (16 segments), `STAGE-DESIGN-SPECS.md` (per-stage build blueprint).

**Deliverables (`docs/`):**
- `notes.html` + `Nataraja-Notes.pdf` — **the Learning Notes (main artifact, 97 lessons).**
- `architecture.html` (interactive Flow + 3-D slab views, logos) + `Nataraja-Architecture.pdf` (light).
- `roadmap.html` + `Nataraja-Roadmap.pdf`.
- `study-guide.html` + `Nataraja-Architecture-Study-Guide.pdf`.
- Original DevOps `.md` docs (git.md, aws.md, cicd.md, …) — untouched.

## 4. Published artifacts (update in place — same URLs)
- **Notes:** https://claude.ai/code/artifact/4c574f15-6f76-42f9-921f-fcb3af6dd7ec
- **Architecture:** https://claude.ai/code/artifact/1d0505c0-a8ab-4ee6-991e-6e86f17164ec
- **Roadmap:** https://claude.ai/code/artifact/e6a356f7-80b2-4c68-b6fa-e09327e9cfb4
- **Study guide:** https://claude.ai/code/artifact/17cb3d73-71fa-473a-960d-d4c465b556f3
> To update from a new session, publish with the **same file path** OR pass the artifact **`url`** +
> **`force:true`** (the scratchpad resets between sessions, so the version link needs re-anchoring).

## 5. ⏳ WHERE WE STOPPED — the Learning Notes deepening
`docs/notes.html` has **97 lessons**: Foundations 0.5 (Lessons 1–10) + Stages 0–12.
We are rebuilding every stage to **"Lesson-1 depth"** (multiple explained step-sections, 2 diagrams,
analogy + insight + warning/bridge callouts, cheat-sheet, self-check).

**Done DEEP:** Foundations 0.5, and Stages **0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10**. ✅
**STILL THIN (need deepening next):** Stages **11, 12**. ⬅️ **RESUME HERE.**
- ~~Stage 10 — Preview Environments (5 topics)~~ ✅ deepened (5e8d98d): 10·1 Ephemeral Envs, 10·2 vcluster vs Namespace, 10·3 external-dns & cert-manager, 10·4 Argo CD ApplicationSets, 10·5 Lifecycle & Teardown.
- Stage 11 — Cloud, IaC & Multi-Region (6 topics)
- Stage 12 — Observability, SRE & Capstone (10 topics)

Current git HEAD when this was written: `5e8d98d` (both branches).

## 6. HOW to continue the deepening (exact procedure)
`docs/notes.html` is the source of truth (self-contained, no external deps). Each stage is a block that
begins with `<div class="stage-banner" id="sN">…</div>` followed by its `<section class="lesson">…</section>` lessons.

**To deepen a stage** (e.g. Stage 10):
1. Read the current stage block in `docs/notes.html` (the span from `id="s10"` up to `id="s11"`).
2. Replace it with deep lessons in the **same HTML shape** the deep stages use. Reusable CSS classes
   already in the file: `.lesson`, `.lesson-h/.lnum`, `h3.step + .n`, `figure/figcaption`,
   `.flow/.fnode/.farrow/.fsplit/.fbranch/.blabel`, `.lanes/.lane/.lh/.lb`, `.tl-row/.tl/.seg`,
   `.callout.analogy|.insight|.warn|.bridge`, `.cheat`, `.selfcheck`. (See any of Stages 4–9 as the template.)
   - Content per topic: 3 step-sections (problem → mechanism → nuance) + 2 diagrams + analogy/insight/warn(or bridge) + cheat + self-check.
   - Keep the stage-banner `id="sN"` so the top nav anchor still works; the nav dot is already set.
   - **Practical tip:** the fast, reliable way is a small throwaway Python script that regex-replaces the
     span: `re.compile(r'<div class="stage-banner" id="s10">.*?(?=<div class="stage-banner" id="s11">)', re.S)`.
     For **Stage 12 (last)** replace up to the final `<div class="foot">…</div>` instead.
     (The helper functions p/step/flow/split/lanes/tl/call/cheat/check/LD used this session lived in
     scratchpad `build_s*_deep.py` — scratchpad is EPHEMERAL and is now gone; just recreate them, they're ~30 lines.)
3. Regenerate the PDF (light theme) — Chrome headless, print wrapper that sets `data-theme="light"`,
   hides `.nav`, forces white bg, page-breaks per lesson/stage-banner. Command shape:
   `"…/Google Chrome" --headless=new --print-to-pdf=Nataraja-Notes.pdf --no-pdf-header-footer --virtual-time-budget=9000 file://…/print.html`
4. Copy both into `docs/`, `git add`, commit on `main`, `git checkout dev && git merge main --ff-only`,
   push both, then **re-publish the notes artifact** (same file path, or url + force).

## 7. Housekeeping still open (optional)
- Stray file `Desktop` at repo root = byte-identical duplicate of `README.md` (untracked) → can delete.
- `.DS_Store` untracked → ignore/delete.
- Foundations 0.5 (L1–L10) are the richest (extra graded self-check on L1). Stages 0–9 are deep but
  slightly lighter than L1 — could add a 3rd diagram to a few if desired.
- After all 12 are deep: consider a README "📚 Docs & Learning" index linking every deliverable.

## 8. Learning cadence (when the user is ready to actually learn/build)
Per `LEARNING-PLAN.md`: teach a concept (from `notes.html`) → user designs in prose → **user writes the
code** → I review against the Definition of Done in `STAGE-DESIGN-SPECS.md` → write an ADR. One stage at
a time; it must run before the next. Stage 0.5 (Python foundations) is where hands-on building starts.
