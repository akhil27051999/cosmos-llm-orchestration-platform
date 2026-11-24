# 0003: CI on every change and a protected `main`

**Status:** Accepted · **Date:** 2026-10-26 · **Milestone:** M0.5

## Context
`main` must always work. Without automation, "I ran the tests locally" depends on memory and discipline, and a
direct push can skip review entirely. CI results must also be reproducible: a red build should mean the code
changed, not the environment.

## Decision
- **GitHub Actions**, one job named `test`, triggered on `pull_request` to `main` **and** on `push` to `main`.
- **Least privilege:** `permissions: contents: read` for the workflow token.
- **Concurrency:** a new push cancels the older run on the same PR; runs on `main` are never cancelled.
- **Pinned everything:** exact package versions in `requirements.txt`, runner `ubuntu-26.04` (not `latest`),
  Python `3.12`, actions by major version.
- **`timeout-minutes: 10`** and a pip cache.
- **Ruleset `protect-main`:** PR required, required check `test`, no bypass (owner included), force-push and
  deletion blocked.
- **Squash merge**, Conventional Commit titles, fix-forward instead of rewriting history.
- The check was **seen failing** on purpose before being trusted.

## Alternatives considered
- **Run tests only on PRs:** misses what actually lands on `main` after the squash merge.
- **`ubuntu-latest` and unpinned deps:** less upkeep, but builds break with no code change.
- **Allow admin bypass:** faster hotfixes, but the most powerful token becomes the easiest way around review.
- **Merge commits or rebase merge:** keep every intermediate commit; squash gives one revertable commit per PR.

## Consequences
- Every change on `main` went through a green PR; one `git revert` undoes one feature.
- Renaming the job breaks merging until the ruleset's required check is updated (the name is a contract).
- Gaps, to close later: transitive dependencies aren't locked (no lock file with hashes), actions are pinned by
  tag rather than commit SHA, no type checking (mypy) or linting in CI. S1 adds image scanning and signing.
