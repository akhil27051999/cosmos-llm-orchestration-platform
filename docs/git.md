# Module 9: Git — Version Control, Internals & Collaboration Workflows

> **Goal:** A deep-dive on Git — enough to understand its object model, run disciplined branching/merging/rebasing, recover from mistakes, and work effectively in a team. Scoped to what a 3–5 yr DevOps/SRE uses every day and gets asked in interviews.

> **Why this matters:** Every pipeline in this repo (CI builds on push, ArgoCD syncs on commit, release tags cut images) is driven by Git. Confident Git use = faster incident recovery, cleaner review, fewer "who force-pushed main?" incidents. Interviewers routinely probe internals (what is a commit?) and recovery (you rebased and lost work — now what?).

> **Scope of this doc:** The `.git/` directory, the three trees, core commands, branching models, merge vs rebase vs cherry-pick, remote operations, hooks, submodules/LFS, recovery, and the conventions we use in this project.

---

## Table of Contents

1. [Why Git (vs SVN, Perforce, etc.)](#why-git-vs-svn-perforce-etc)
2. [Git Internals — The Object Model](#git-internals--the-object-model)
3. [The Three Trees — Working Dir, Index, HEAD](#the-three-trees--working-dir-index-head)
4. [Core Commands You Must Own](#core-commands-you-must-own)
5. [Branching Models](#branching-models)
6. [Merge vs Rebase vs Cherry-Pick](#merge-vs-rebase-vs-cherry-pick)
7. [Remotes, Push/Pull/Fetch](#remotes-pushpullfetch)
8. [Undo, Recovery & Reflog](#undo-recovery--reflog)
9. [Advanced Features](#advanced-features)
10. [Hooks](#hooks)
11. [.gitignore, .gitattributes, Line Endings](#gitignore-gitattributes-line-endings)
12. [Submodules, Subtrees, LFS](#submodules-subtrees-lfs)
13. [Worktrees](#worktrees)
14. [Troubleshooting (Real-World Scenarios)](#troubleshooting-real-world-scenarios)
15. [Interview Q&A](#interview-qa)
16. [STAR Stories](#star-stories)
17. [Conventions Used in This Project](#conventions-used-in-this-project)
18. [Cheat Sheet](#cheat-sheet)

---

## Why Git (vs SVN, Perforce, etc.)

| Aspect | Git | SVN / CVS | Perforce |
|--------|-----|-----------|----------|
| Model | **Distributed** — every clone is a full repo | Centralized — server is truth | Centralized (with streams) |
| Branching | Cheap (a ref = a 40-byte file) | Expensive (server-side copy) | Medium |
| Works offline | Full history, commit, branch offline | No (needs server) | Partial |
| Merge | 3-way, reliable | Often painful | OK |
| Performance | Fast (local ops) | Slow on large repos | Fast on huge monorepos |
| Storage | Content-addressable, compressed | File-based | Depot, optimized for binaries |

**Key insight:** "distributed" means there's no special server — `origin` is just a convention. Your laptop's clone is a peer. The history is cryptographically linked — impossible to silently rewrite past commits.

---

## Git Internals — The Object Model

Everything in Git is a **content-addressable object** stored under `.git/objects/`. The filename is the SHA-1 (or SHA-256 on newer Git) of the content.

### Four object types

```
┌──────────────────────────────────────────────────────────────────────┐
│  commit  →  points to a tree  +  parent commit(s)  +  author + msg   │
│     │                                                                │
│     ▼                                                                │
│   tree    →  directory listing:  (mode, type, SHA, name) per entry   │
│     │                                                                │
│     ├──► blob  →  file content (bytes)                               │
│     └──► tree  →  subdirectory                                       │
│                                                                      │
│  tag    →  annotated tag:  object SHA + tagger + msg (for releases)  │
└──────────────────────────────────────────────────────────────────────┘
```

| Object | Contains | Points to |
|--------|----------|-----------|
| **blob** | Raw file bytes | — |
| **tree** | List of `<mode> <type> <sha>\t<name>` entries | blobs + subtrees |
| **commit** | Tree SHA, parent SHA(s), author, committer, timestamp, message | tree + parent commit(s) |
| **tag** (annotated) | Object SHA, type, tagger, message | any object |

**Commit graph** = DAG (Directed Acyclic Graph). Merges have 2+ parents; octopus merges more.

### Inspecting objects

```bash
git cat-file -t <sha>            # type (commit/tree/blob/tag)
git cat-file -p <sha>            # pretty-print contents
git cat-file -s <sha>            # size

git ls-tree HEAD                 # show root tree of latest commit
git ls-tree -r HEAD              # recursive
git log --oneline --graph --all  # visualize the DAG
```

**Demonstration:**
```bash
$ git cat-file -p HEAD
tree  6f1a94d...
parent 7ca49ea...
author Akhil <...> 1745068800 +0530
committer Akhil <...> 1745068800 +0530

Retry docker push up to 3 times to tolerate proxy flakiness
```

### References (`refs`)

References are human-readable names that point at a commit SHA. They live under `.git/refs/`:

```
.git/refs/heads/main       ← branch "main" = file containing a SHA
.git/refs/heads/dev
.git/refs/tags/v1.0.0
.git/refs/remotes/origin/main
.git/HEAD                  ← current branch:  "ref: refs/heads/main"
```

When you `git checkout` a branch, `HEAD` points at that branch ref. When you check out a specific SHA, `HEAD` points at the SHA directly — **detached HEAD**.

### The index (staging area)

`.git/index` is a **binary file** listing the next commit's tree: every path, its mode, its blob SHA, and stat info for fast dirty-check. `git add` updates it. `git commit` writes a new tree from it.

### Packfiles

Loose objects get repacked into `.git/objects/pack/*.pack` with delta compression — especially for many versions of the same file. `git gc` (automatic or manual) does this.

### SHA-1 → SHA-256

Git is migrating from SHA-1 (collision attacks possible but practically hard) to SHA-256. Most repos still use SHA-1; interoperability with servers like GitHub is the gating factor.

---

## The Three Trees — Working Dir, Index, HEAD

```
┌────────────────┐   git add    ┌────────────────┐   git commit   ┌────────────────┐
│  Working Dir   │ ───────────► │  Index         │ ─────────────► │  HEAD          │
│  (files on     │              │  (staging)     │                │  (last commit) │
│   disk)        │ ◄─────────── │                │ ◄───────────── │                │
└────────────────┘  git restore └────────────────┘  git reset    └────────────────┘
                  git checkout                      git reset
```

| Tree | Where it lives | How to inspect |
|------|----------------|----------------|
| Working directory | Your files on disk | `ls`, editor |
| Index | `.git/index` | `git ls-files --stage`, `git diff --cached` |
| HEAD | `.git/refs/heads/<branch>` → commit → tree | `git show HEAD`, `git log -1` |

**The key mental model:** every Git command is either:
- **Moving content** between these three trees (`add`, `restore`, `checkout`, `reset`), or
- **Recording** the Index as a new commit (`commit`), or
- **Moving HEAD/branch pointers** (`checkout`, `reset`, `branch`, `merge`, `rebase`), or
- **Syncing with remotes** (`fetch`, `push`).

Once this clicks, everything else is a variation.

---

## Core Commands You Must Own

### Inspect

```bash
git status                        # working tree + index state
git status -s                     # short, scriptable
git diff                          # working vs index
git diff --cached                 # index vs HEAD (what will be committed)
git diff HEAD                     # working vs HEAD
git diff origin/main...HEAD       # changes on your branch since it diverged
git log --oneline --graph --decorate --all
git log -p <path>                 # diffs touching a path
git log --follow <path>           # follow renames
git log -S"<string>"              # pickaxe — commits that added/removed a string
git log -G"<regex>"               # pickaxe regex
git blame <file>                  # line-by-line last author
git show <sha>                    # commit + diff
git reflog                        # local history of HEAD movements (lifesaver)
```

### Stage + Commit

```bash
git add <paths>                   # stage specific paths
git add -p                        # stage hunks interactively
git add -u                        # stage tracked-file modifications (no new files)
git commit -m "msg"
git commit --amend                # rewrite last commit (only if unpushed)
git commit --fixup=<sha>          # mark as fixup of an earlier commit (for autosquash rebase)
```

**Discipline:** one logical change per commit. `git add -p` is how you enforce it even when edits overlap.

### Branch

```bash
git branch                        # list local
git branch -a                     # + remotes
git branch -vv                    # show tracking
git branch <name>                 # create branch at HEAD
git checkout -b <name>            # create + switch
git switch <name>                 # modern alternative to checkout
git switch -c <name>              # create + switch
git branch -d <name>              # delete merged branch
git branch -D <name>              # force delete (unmerged)
git branch --merged main          # branches fully merged into main (candidates for cleanup)
```

### Restore / Reset / Revert — know the difference

| Command | Affects | Keeps working tree? | Use |
|---------|---------|---------------------|-----|
| `git restore <path>` | Working tree | — | Undo unstaged edits |
| `git restore --staged <path>` | Index | Yes | Un-add (inverse of `git add`) |
| `git reset --soft <sha>` | HEAD only | Yes (changes re-staged) | Re-do commits (e.g., squash into one) |
| `git reset --mixed <sha>` (default) | HEAD + index | Yes | Un-commit + un-add, keep edits |
| `git reset --hard <sha>` | HEAD + index + working tree | **No — destructive** | Nuke to a known state |
| `git revert <sha>` | Creates a new commit | Yes | Safe undo of a pushed commit |

**Rule:** `reset --hard` is safe on local-only work; `revert` is safe on shared history. Never `reset --hard` after you've pushed — someone else has your commits.

---

## Branching Models

### 1. Trunk-Based Development (preferred at most modern orgs)

```
main ────●────●────●────●────●────●────●────●────►
          \        \        \
           short-lived feature branches (hours–1–2 days)
           merge back quickly via PR
```

- One long-lived branch: `main`.
- Short branches for features, merged quickly.
- Feature flags for in-progress work.
- CI on every commit; main is always releasable.
- Works with CD: every main commit can be promoted.

### 2. GitHub Flow

Trunk-based variant used by GitHub:
1. Branch off `main`.
2. Push + open a PR.
3. Review + discuss.
4. Merge to `main` when green.
5. Deploy `main` (continuously).

### 3. GitFlow (legacy, complex)

```
 main ─●────────────────●─────────────●──────────►   (releases, tags)
        \              /             /
         release/1.0  ●──●          ●
        / \          /  \          /
 develop●──●───●────●────●────●────●───●──────────►
         \                    /
          feature/x──●──●──●
```

Branches: `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`.
- Heavier. Suits versioned/shipped software (OS releases, enterprise products).
- Overkill for web SaaS — most orgs moved off of it.

**When to pick what:**
| Scenario | Model |
|----------|-------|
| Continuous deployment, web/SaaS | Trunk-based / GitHub Flow |
| Mobile apps with app-store release gates | GitHub Flow + release branches for stores |
| Long-lived supported versions (v1.x, v2.x) | GitFlow or release branches |
| Monorepo, many teams | Trunk + feature flags + build targeting |

**This project uses:** trunk-based on `main`; `dev` exists but we keep it at parity (see Module 3 for CI triggers). Force-sync policy: `main` is canonical; `dev` can be reset to `main` when they drift.

---

## Merge vs Rebase vs Cherry-Pick

### Merge

```
            A---B---C   (feature)
           /
  D---E---F---G---H     (main)
                     \
                      M (merge commit)
```

- `git merge feature` into main → creates a **merge commit** with 2 parents.
- Preserves history exactly; non-destructive.
- Use for: long-lived branches, integration of large features, anything already pushed/shared.

**Fast-forward merge:** if `main` hasn't diverged from `feature`, git just moves the pointer — no merge commit.
- `--ff-only` — refuse unless FF possible. Useful for dependents (e.g., moving `dev` to `main`).
- `--no-ff` — always create a merge commit. Preserves the fact a feature branch existed.

### Rebase

```
            A---B---C   (feature)
           /
  D---E---F---G---H     (main)

  after git rebase main on feature:

  D---E---F---G---H     (main)
                   \
                    A'---B'---C'   (feature, rewritten on top)
```

- `git rebase main` on `feature` → replays `feature`'s commits on top of `main`, new SHAs.
- Result is **linear history**.
- Use for: polishing your branch before PR, keeping a feature up-to-date with main during development.
- **Don't rebase commits that others have pulled.** You rewrite history → their clones are now divergent.

**Interactive rebase** (`git rebase -i`) is the workhorse for cleaning history:
```
pick 7a1b2c3 WIP initial
squash c4d5e6f fix typo
squash 8f9g0h1 rename variable
reword 2i3j4k5 Add user service
```

Actions: `pick`, `reword` (change message), `edit` (stop to amend), `squash` (combine + edit msg), `fixup` (combine silently), `drop`.

### Cherry-Pick

```
  main    ──A───B───C───D───►
  release           ●
  git cherry-pick D on release:
  release           ●───D'
```

- Copy a commit from one branch onto another (new SHA).
- Use for: backporting a fix to a release branch, extracting one commit from a PR.
- Pitfall: if the same commit ends up on main *and* a release branch via cherry-pick, they're **different SHAs** — merge later will see them as duplicates. Range-diff helps.

**In this project:** when `dev` was out of sync with `main`, we verified the dev-only commits were cherry-picks (same content, different SHA) with `git range-diff`, then reset `dev` to `main`.

### When to use which

| Situation | Command |
|-----------|---------|
| Completed feature, merging to main | `merge` (with PR + squash on GitHub) |
| Keeping my WIP branch current with main | `rebase main` |
| Cleaning up messy WIP into logical commits | `rebase -i` |
| Backporting a hotfix to 2 release branches | `cherry-pick` |
| Emergency undo of a published commit | `revert` |
| Replaying my branch after a force-push upstream | `rebase --onto` |

---

## Remotes, Push/Pull/Fetch

### Remotes

```bash
git remote -v                     # list
git remote add upstream <url>     # add a 2nd remote (common for forks)
git remote set-url origin <url>   # change URL
```

### Fetch vs Pull

```bash
git fetch origin                  # download objects + update remote refs; DOES NOT touch your branch
git fetch --prune                 # also delete refs for branches removed on remote
git pull                          # = fetch + merge (default) or fetch + rebase (if configured)
git pull --rebase                 # safer default: linearize
```

**Best practice:** `fetch` → inspect (`git log origin/main...HEAD`) → decide → `merge`/`rebase`. Never blind-`pull` on a shared branch.

### Push

```bash
git push                          # push current branch to its upstream
git push -u origin <branch>       # set upstream on first push
git push --force-with-lease       # force, but only if remote matches our expectation — safer than --force
git push --force                  # dangerous; overwrites even if someone else pushed
git push --tags                   # include tags
git push origin :<branch>         # delete remote branch (old syntax)
git push origin --delete <branch> # delete remote branch (modern)
```

**`--force-with-lease` rule:** always prefer over `--force`. It fails instead of clobbering if the remote moved since your last fetch.

### Refspecs (advanced)

```
git push origin feature:main       # push local "feature" to remote "main"
git fetch origin main:my-tracking  # fetch remote "main" into local branch "my-tracking"
```

Most day-to-day usage hides this behind `git push` conventions.

### Protocols

- **HTTPS** — easy, works behind firewalls, needs credential helper (or GitHub PAT).
- **SSH** — key-based, fast, common for devs.
- **Git protocol** — legacy.

Credential helpers: `osxkeychain` (macOS), `manager-core` (Windows), `libsecret` (Linux), `cache` (in-memory, timeout).

---

## Undo, Recovery & Reflog

### The reflog is your time machine

Every HEAD movement is logged locally under `.git/logs/HEAD` — including resets, rebases, force-moves.

```bash
git reflog                        # list HEAD history
git reflog show <branch>          # specific branch
git reset --hard HEAD@{3}         # go back 3 movements
git checkout HEAD@{yesterday}     # time-based
```

**Rule of thumb:** if you can name something, you can recover it. Commits are kept by `git gc` for 30 days (default `gc.reflogExpire`) — plenty of time.

### Common recovery scenarios

| Situation | Recovery |
|-----------|----------|
| `git reset --hard` killed uncommitted work | Not recoverable (never committed). Moral: commit early, amend later. |
| `git reset --hard` killed committed work | `git reflog` → find prior SHA → `git reset --hard <sha>` |
| Bad rebase, branch is broken | `git reflog` → find pre-rebase SHA → `git reset --hard <sha>` |
| Deleted a branch | `git reflog` on any HEAD movement that referenced it → `git branch <name> <sha>` |
| Force-pushed bad to remote | Co-worker has it: `git fetch origin; git log` → find the SHA → push it back. Or use GitHub "activity" on branches. |
| Stashed and forgot | `git stash list` → `git stash show -p stash@{N}` → `git stash apply` |
| Commit on wrong branch | `git log` to find SHA → switch to right branch → `git cherry-pick <sha>` → return and `git reset --hard HEAD~1` |

### `git fsck` for dangling objects

When reflog entries expire, unreferenced objects become "dangling" before `gc` sweeps them:
```bash
git fsck --lost-found             # lists dangling commits/blobs
git show <dangling-sha>
```

---

## Advanced Features

### Stash

```bash
git stash push -m "WIP"           # stash tracked changes
git stash push -u -m "WIP"        # include untracked
git stash list
git stash show -p stash@{0}       # diff
git stash apply stash@{0}         # apply, keep stash
git stash pop                     # apply + drop
git stash push -m "only file" path/to/file   # partial stash
git stash drop stash@{0}
```

Stashes are commits under `refs/stash` — safe but orphan-like; don't rely on them for long-term storage.

### Bisect — binary search for a bad commit

```bash
git bisect start
git bisect bad                    # current is bad
git bisect good v1.0              # v1.0 was good
# Git checks out the midpoint; test...
git bisect good                   # or git bisect bad
# Repeat until git identifies the first bad commit
git bisect reset
```

**Automate:** `git bisect run ./test.sh` runs your script on each step, reporting pass/fail.

### Tags

```bash
git tag v1.0.0                    # lightweight tag (just a name)
git tag -a v1.0.0 -m "Release"    # annotated (object with author, date, msg — recommended for releases)
git tag -s v1.0.0 -m "Release"    # GPG-signed
git push origin v1.0.0            # push a single tag
git push --tags                   # push all tags
git tag -d v1.0.0                 # delete locally
git push origin :refs/tags/v1.0.0 # delete remote
```

Release convention: annotated, signed tags. CI often triggers off `tag push`.

### Signed commits/tags

```bash
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
git commit -S -m "signed"
git tag -s v1.0.0 -m "signed"
git log --show-signature
```

GitHub shows "Verified" next to signed commits. Increasingly expected in regulated orgs.

### `rev-parse` — resolving what you mean

```bash
git rev-parse HEAD                # SHA
git rev-parse HEAD~3              # SHA of 3 commits ago
git rev-parse origin/main
git rev-parse --abbrev-ref HEAD   # current branch name
git rev-parse --show-toplevel     # repo root
```

### `range-diff` — compare two branches' commits

```bash
git range-diff main...feature     # shows which commits are new, rebased, dropped, or unchanged
```

Essential when you rebased and want to prove content didn't change. We used it earlier in this project to verify dev-only commits were content-identical duplicates of commits on main.

### Autosquash workflow

```bash
git commit --fixup=<sha>          # creates "fixup! <original msg>"
...
git rebase -i --autosquash <base> # fixups slot in right after the target commit
```

Cleans WIP into a tidy history without manually reordering.

### Sparse checkout & partial clone (monorepos)

```bash
git clone --filter=blob:none <url>            # partial clone — blobs on demand
git sparse-checkout init --cone
git sparse-checkout set services/flask-api    # only check out a subdirectory
```

Required for working on huge monorepos without cloning everything.

---

## Hooks

Local scripts under `.git/hooks/` (not committed by default). Triggered by git events.

| Hook | When | Common use |
|------|------|-----------|
| `pre-commit` | Before commit is made | Lint, format, run quick tests |
| `commit-msg` | After msg written, before commit recorded | Enforce conventional commits, add Jira ID |
| `pre-push` | Before push | Run full tests |
| `post-commit` | After commit | Notify, tag |
| `prepare-commit-msg` | Before editor opens | Template message |
| `pre-rebase`, `post-checkout`, `post-merge` | As named | Env setup (install deps, rebuild) |

**Server-side:**
| Hook | When | Use |
|------|------|-----|
| `pre-receive`, `update` | On push to remote | Reject pushes that violate policy |
| `post-receive` | After push accepted | Trigger deploy / notify |

**Tooling:** `pre-commit` framework (Python) is the standard way to share hooks across a team. Defines `.pre-commit-config.yaml`, installs into `.git/hooks/`, version-controlled centrally.

---

## .gitignore, .gitattributes, Line Endings

### `.gitignore`

Patterns of files Git should not track. Precedence (most specific first):
1. Command-line `--exclude`
2. `.gitignore` in any directory (cascades)
3. `$HOME/.config/git/ignore` (global)
4. `.git/info/exclude` (repo-local, not shared)

**Gotcha:** `.gitignore` does **not** untrack already-tracked files. Use `git rm --cached <file>` after adding it to `.gitignore`.

### `.gitattributes`

Controls per-path behavior:

```
*.sh        text eol=lf                 # force LF line endings (prevent Windows CRLF drift)
*.pdf       binary                      # no diff, no text munging
*.lock      merge=ours                  # always keep "ours" on merge conflicts
*.ipynb     filter=nbstripout           # custom filter (clean notebooks on commit)
```

### Line endings

Cross-platform pain. Recommended: **LF in repo, LF in working tree** (since macOS/Linux are LF-native and modern Windows editors handle LF fine). Configure:

```
git config --global core.autocrlf input   # macOS/Linux — commit LF
git config --global core.autocrlf true    # legacy Windows — checkout CRLF, commit LF
```

**Best practice:** use `.gitattributes` (versioned) instead of relying on per-user `autocrlf`.

---

## Submodules, Subtrees, LFS

### Submodules

Nested repos pinned at a specific commit.

```bash
git submodule add <url> path/
git submodule update --init --recursive   # clone submodules on fresh checkout
git submodule update --remote             # advance to latest remote commit
```

- Tracks `gitlink` in the parent tree.
- Painful in practice: forgotten `--init`, detached HEAD inside the submodule, different branch per dev.
- Use only when you genuinely need independent repos that must be pinned.

### Subtrees

```bash
git subtree add --prefix=vendor/lib https://… main --squash
git subtree pull --prefix=vendor/lib https://… main --squash
```

Embed another repo's history into yours. Unlike submodules, clone just works — no extra step. Downside: history gets intermixed.

### Git LFS (Large File Storage)

For big binaries (media, models, large PDFs). Actual content stored in LFS server (GitHub/Gitlab provide one); repo stores a pointer.

```bash
git lfs install
git lfs track "*.psd"
git add .gitattributes
git add design.psd
git commit -m "Add design"
```

Without LFS, large binaries balloon repo size forever — hard to remove from history (see BFG Repo-Cleaner).

---

## Worktrees

Work on multiple branches **simultaneously** without stashing:

```bash
git worktree add ../repo-hotfix hotfix/bug-123
cd ../repo-hotfix
# hack hack; git commit; git push
git worktree remove ../repo-hotfix
git worktree list
```

Each worktree has its own working tree + HEAD, but shares `.git/objects`. Perfect for:
- Long-running build in one worktree while reviewing a PR in another.
- Running a bisect in one worktree without disturbing your main work.

---

## Troubleshooting (Real-World Scenarios)

1. **"fatal: refusing to merge unrelated histories."** You `git pull`ed into a repo whose history has no common ancestor with origin's. Usually: you init'd locally, then tried to pull from a remote that has different history. `git pull --allow-unrelated-histories` if it's truly the same project, else `git clone` fresh and copy your work over.

2. **"Your branch and 'origin/main' have diverged."** You and the remote both added commits. Options: `git pull --rebase` (linearize — your commits on top), or `git merge origin/main` (create a merge commit). Pick based on team policy.

3. **Merge conflict, can't find the markers.** `git diff --name-only --diff-filter=U` lists conflicted files. Edit, then `git add` + `git commit` (or `git rebase --continue`). Abort with `git merge --abort` / `git rebase --abort`.

4. **Force-pushed someone else's branch by mistake.** Bad. Immediately: `git reflog origin/<branch>` isn't directly possible, but **anyone with the old SHA in their local reflog can push it back**. Ask the team; the likely owner's laptop has it. That's why `--force-with-lease` exists.

5. **"fatal: Not a git repository."** You're outside a repo, or `.git/` was accidentally deleted. `git status` to confirm; `git init` only if you truly want to start fresh.

6. **Pushed a secret by mistake.** (a) Rotate the secret IMMEDIATELY — once public, treat as compromised. (b) Remove from history: BFG Repo-Cleaner or `git filter-repo` (rewrites history). (c) Force-push (with team coordination). (d) On GitHub, contact support to purge PR view. Prevention: pre-commit hook + secret scanner + `.gitignore .env`.

7. **Giant file in history bloating clone time.** `git filter-repo --path big.bin --invert-paths` rewrites history to remove it. Force-push + everyone re-clones.

8. **`git pull` says "Already up to date" but my code doesn't match production.** You might be on the wrong branch (`git branch --show-current`), or tracking the wrong remote branch (`git branch -vv`), or production isn't at `origin/main` HEAD. Compare with `git log origin/main -1` and `git fetch` first.

9. **Detached HEAD.** You `git checkout <sha>` or checked out a tag. Commits here aren't on any branch → will be GC'd after reflog expires. Fix: `git switch -c new-branch` to capture current HEAD as a branch.

10. **Merge conflict on a generated file (`package-lock.json`, `go.sum`).** Don't hand-edit. Resolve by regenerating: check out one side, re-run the tool (`npm install`, `go mod tidy`), commit. Configure `.gitattributes` with `merge=ours`/custom driver for known-generated files.

11. **`.gitignore` not ignoring a file.** Already tracked. `git rm --cached <file>` to untrack, then commit. `.gitignore` only prevents *new* files from being added.

12. **Committed to `main` instead of a branch.** Before push: `git branch feature-x`, `git reset --hard HEAD~N`, `git checkout feature-x`. After push: `git revert` on main + cherry-pick to a new branch + PR.

13. **`git log` shows commits but `git log -- <path>` shows nothing.** `--follow <path>` to trace through renames. Without it, a rename breaks the chain.

14. **Pre-commit hook fails with "command not found" on shared runner.** Hook script relies on locally-installed tool; runner doesn't have it. Use `pre-commit` framework to pin tool versions; or install in CI before hooks run; or skip in CI explicitly.

15. **`git push` rejected — "non-fast-forward."** Remote has commits you don't. `git pull --rebase` then push again. Only `--force-with-lease` if you deliberately want to overwrite.

---

## Interview Q&A

1. **What is a commit, literally?**
   > An object whose content is: a tree SHA (snapshot of the working directory at that time), one or more parent commit SHAs, author/committer metadata, and a message. It is identified by the SHA of its own content.

2. **How does Git store files — diffs or snapshots?**
   > **Snapshots.** Each commit references a full tree that references full blobs. Unchanged files share the same blob SHA — deduplicated by content. Packfiles add delta compression for storage efficiency, but the logical model is snapshots.

3. **What's the difference between `git fetch`, `git pull`, and `git pull --rebase`?**
   > `fetch` downloads objects and updates remote-tracking refs (`origin/main`) — working branch untouched. `pull` = fetch + merge. `pull --rebase` = fetch + rebase your commits on top. Prefer fetch + inspect + explicit merge/rebase for shared branches.

4. **Merge vs rebase — when to use each?**
   > Merge preserves exact history with a merge commit; safe on shared branches. Rebase rewrites your branch on top of the target for a linear history; never use on commits others already have.

5. **What does `git reset --hard` do that `git reset --mixed` doesn't?**
   > `--hard` also throws away working-directory changes. `--mixed` (default) moves HEAD + index but keeps edits in your working tree.

6. **Revert vs reset?**
   > `revert` creates a *new* commit that undoes a target commit — safe for published history. `reset` rewrites history by moving HEAD — only safe locally.

7. **You committed to the wrong branch. What do you do?**
   > If not pushed: create the right branch at current HEAD, reset the wrong branch back, then switch. Push normally. If pushed: revert on the wrong branch + cherry-pick to the right branch.

8. **What is `git cherry-pick` and when is it dangerous?**
   > Copies a commit onto another branch with a new SHA. Dangerous because the two copies look different to future merges → duplicate-looking history. Use `git range-diff` to verify equivalence.

9. **Describe the Git index.**
   > A binary file (`.git/index`) listing the paths, modes, and blob SHAs that will make up the next commit. `git add` updates it; `git commit` converts it into a tree and writes a commit.

10. **What's `HEAD`?**
    > A symbolic reference to the current commit — usually via a branch ref (`ref: refs/heads/main`). "Detached HEAD" means it points directly at a SHA with no branch.

11. **How does `.gitignore` work, and why doesn't it untrack?**
    > Git consults `.gitignore` only when deciding whether to *track* new files. Already-tracked files are unaffected; use `git rm --cached` to untrack.

12. **What's the reflog and why is it important?**
    > A local log of every HEAD (and branch ref) movement, kept for 90 days by default. Recovers from "lost" commits — resets, bad rebases, deleted branches. Purely local; does not help if the commit never existed on your machine.

13. **How do you find which commit introduced a bug?**
    > `git bisect` — mark a known-good commit and a known-bad, Git binary-searches by checking out midpoints. `git bisect run ./test.sh` automates it.

14. **What's a fast-forward merge?**
    > When the target branch has no divergent commits, git simply moves the branch pointer to the tip of the source branch — no merge commit. Use `--no-ff` to force a merge commit anyway.

15. **`--force` vs `--force-with-lease`?**
    > `--force` blindly overwrites the remote branch. `--force-with-lease` fails if the remote has moved since your last fetch — protects against clobbering someone else's push. Always prefer `--force-with-lease`.

16. **How do you rewrite the last commit's message?**
    > `git commit --amend` (replaces the commit — new SHA). If pushed, requires `--force-with-lease`.

17. **How would you remove a file from the entire history?**
    > `git filter-repo --path <file> --invert-paths` (new tool), or `BFG Repo-Cleaner`. Then `git push --force-with-lease` and everyone re-clones. Also rotate any secrets in that file — assume compromised.

18. **What's a submodule and what are its pitfalls?**
    > A repo nested at a specific commit inside another repo. Pitfalls: must `git submodule update --init --recursive` after clone; detached HEAD inside; easy to update incorrectly; conflicts on submodule bumps are common.

19. **Explain the object types: blob, tree, commit, tag.**
    > Blob = file contents. Tree = directory listing (name → blob/tree SHA + mode). Commit = tree SHA + parent SHAs + author/committer + msg. Annotated tag = object reference + metadata (lightweight tag = just a ref file).

20. **Describe a git workflow for a team of 10 devs.**
    > Trunk-based: short-lived feature branches (`feature/<jira-id>-<slug>`), opened as PRs into `main`, squash-merged with linked ticket in title. CI blocks merge on failing tests/lint. Main auto-deploys. Releases = tags on main.

21. **What does `git rebase --onto` do?**
    > Replays a range of commits onto a different base. Handy when your feature branched off an old branch that has since been rewritten: `git rebase --onto main old-base feature`.

22. **Why do monorepos use partial clone / sparse checkout?**
    > Full clone of a huge monorepo is slow and uses tons of disk. Partial clone fetches blobs on demand. Sparse checkout shows only the paths a dev needs. Together they keep working trees manageable.

23. **`git log --oneline` shows `(HEAD -> main, origin/main)`. What does that mean?**
    > Current HEAD is at the `main` branch, which is at the same SHA as `origin/main`. I.e., local and remote are in sync.

24. **How do you cancel an in-progress merge?**
    > `git merge --abort`. Or `git rebase --abort` / `git cherry-pick --abort` / `git am --abort` for those. Only works while the operation is ongoing.

25. **Squash merges vs merge commits on GitHub — tradeoffs?**
    > Squash: one commit per PR on main — clean linear history, easy `git bisect`, lose in-PR commits. Merge commit: preserve every commit on the branch plus a merge point — more detail, noisier. Most teams prefer squash for apps, merge for libraries where intermediate commits might matter.

---

## STAR Stories

### Story 1 — Leaked Webhook in Commit History

**Situation.** During a weekend refactor, I committed an Alertmanager Slack webhook URL into `values.yaml`. It was pushed to `main` before I noticed.

**Task.** Remove the secret from history and prevent recurrence.

**Action.** (1) Rotated the webhook in Slack immediately — assumed compromised. (2) Switched `values.yaml` to read from a Kubernetes Secret (`slack_api_url_file`) instead of the literal URL. (3) Rewrote history with `git filter-repo --replace-text <sed-file>` mapping the old URL to `REDACTED`. (4) Force-pushed with `--force-with-lease` after coordinating with the two other contributors who had the repo cloned. (5) Added a `pre-commit` framework config with `detect-secrets` and `gitleaks` so any future secret fails CI *and* blocks locally. (6) Enabled GitHub's secret scanning alerts.

**Result.** Webhook rotated within 20 min. Secret purged from all reachable refs. `pre-commit` caught two additional near-misses in the following months. Drill became a team onboarding item: "how to remove a secret from history."

### Story 2 — The CI That Kept Running on the Wrong Branch

**Situation.** Our CI pipeline's `update-helm` job pushed image tags via `git checkout main` → `sed` → `push`. But when the trigger ran from a feature branch, the sed was applied to main's values.yaml, and the push went to main — regardless of which branch merged.

**Task.** Ensure image-tag commits always land on the branch that produced the image.

**Action.** Reproduced by pushing a test image tag from `dev`. Confirmed values.yaml was bumped on main even though the image came from a `dev` build. Fix: the workflow's `update-helm` job always checks out `main` — correct for our GitOps setup, but the **job was running for any branch push**. Refactored the workflow so the `update-helm` job only runs when `github.ref == 'refs/heads/main'`; feature-branch pushes skip it. Added a dry-run mode for non-main branches that prints the intended change without committing.

**Result.** No more cross-branch contamination. Also revealed two other workflows with similar assumptions; fixed those too. Added a short "CI trigger semantics" section to the runbook so on-call doesn't get surprised.

### Story 3 — Rescuing a Lost Afternoon

**Situation.** A teammate ran `git reset --hard origin/main` while on a local feature branch, wiping an afternoon's work.

**Task.** Recover without anyone admitting anything on Slack.

**Action.** Walked them through `git reflog` on a screenshare. The reset was movement 1; the prior HEAD was the pre-reset commit. `git reset --hard HEAD@{1}` restored the branch to the lost state — full working tree and all commits. Total time: under 2 minutes.

**Result.** Work recovered; 0 lost time. Used the moment to write a 1-page "git recovery" doc for the team — reflog, `fsck --lost-found`, `stash list`, typical reset scenarios. Reduced Slack DMs about lost work by ~100%.

### Story 4 — Diverged Branches After a Rebase

**Situation.** `dev` and `main` on a project had diverged: 4 dev-only commits with the same messages as 4 commits on main, plus 22 extra commits on main. Suspected: someone cherry-picked dev commits to main and never synced back.

**Task.** Make `dev` and `main` identical without losing work.

**Action.** Ran `git range-diff main...origin/dev` to **prove content equivalence** — the 4 dev commits were byte-for-byte the same diffs as 4 on main, just different SHAs from the cherry-pick. Confirmed no unique work would be lost. `git checkout dev; git reset --hard main; git push --force-with-lease origin dev`. Later, kept the two in sync by treating `main` as canonical and fast-forwarding `dev` after every merge.

**Result.** Branches reunified; CI stopped double-triggering on duplicate commits. Documented the rule: "don't cherry-pick across long-lived branches — use merges or resets." Used `range-diff` became a standard tool for anyone claiming "I just rebased, the content is identical."

---

## Conventions Used in This Project

| Area | Convention |
|------|------------|
| **Main branch** | `main` (GitHub default; was `master` pre-2020) |
| **Secondary** | `dev` — kept at parity with `main`; reset if drifted |
| **Feature branches** | `feature/<short-slug>` or `fix/<short-slug>` |
| **Commit messages** | Imperative mood ("Add X", not "Added X"). First line ≤70 chars. Blank line. Body if needed. Trailer `Co-Authored-By:` when AI-assisted. |
| **Image tags** | Commit SHA prefix (`${GITHUB_SHA::7}`) — 1:1 with a known commit |
| **Merge strategy** | Fast-forward when possible; squash via GitHub PRs for multi-commit features |
| **Force push** | Only `--force-with-lease`; only on branches you own |
| **Tags** | Annotated, future: signed. `v<semver>` format. |
| **CI triggers** | `paths:` filter so doc-only changes don't trigger image builds |
| **`[skip ci]`** | Used in CI-authored commits (e.g., auto-bump values.yaml) to avoid recursive builds |

---

## Cheat Sheet

### Day-to-day
```bash
git status
git diff                  git diff --cached
git add -p
git commit -m "msg"       git commit --amend
git push                  git push --force-with-lease
git switch <branch>       git switch -c <new>
git fetch --prune
git pull --rebase
git log --oneline --graph --decorate --all -20
git blame <file>
git stash push -u -m "wip"   git stash pop
```

### Recovery
```bash
git reflog                     # where did I come from?
git reset --hard HEAD@{N}      # time-travel
git fsck --lost-found          # orphaned objects
git merge --abort              # escape
git rebase --abort
```

### History surgery
```bash
git rebase -i <base>                    # squash, reword, drop
git commit --fixup=<sha> && git rebase -i --autosquash <base>
git cherry-pick <sha>
git revert <sha>
git range-diff <a>...<b>                # prove two histories are content-equivalent
```

### Remote management
```bash
git remote -v
git remote add upstream <url>
git fetch upstream
git rebase upstream/main
git push origin <branch>
git push origin --delete <branch>
git push origin <tag>
```

### Inspection
```bash
git cat-file -p <sha>                # see object contents
git ls-tree -r HEAD                  # files in HEAD
git show <sha>:<path>                # file at a commit
git log --all --oneline --source -- <path>
```

---

## Further Reading

- [Pro Git Book](https://git-scm.com/book/en/v2) — the canonical reference, free.
- [Git from the Bottom Up](https://jwiegley.github.io/git-from-the-bottom-up/) — object model deep dive.
- [Think Like (a) Git](https://think-like-a-git.net/) — conceptual model.
- [Oh Shit, Git!?!](https://ohshitgit.com/) — recovery cookbook.
- [Conventional Commits](https://www.conventionalcommits.org/) — commit-message standard.
- [git-filter-repo](https://github.com/newren/git-filter-repo) — modern history rewriting.
