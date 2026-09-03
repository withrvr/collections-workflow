# Contributing

This repo is not currently accepting outside contributions. This file
documents the actual working conventions it follows, for anyone reviewing
or continuing the work.

## Workflow

One branch per phase (`phase/NN-name`), one pull request per phase,
tagged on merge. See [`MASTER_PLAN.md`](MASTER_PLAN.md) section 8 for
the full git workflow — commit message format (Conventional Commits),
branch naming, the PR template
([`.github/pull_request_template.md`](.github/pull_request_template.md)),
and the SemVer tagging scheme.

## Developing

For local setup, running the stack, tests, linting, and pre-commit
hooks, see [`development.md`](development.md) (base stack) and
[`backend/app/collections/docs/DEVELOPMENT.md`](backend/app/collections/docs/DEVELOPMENT.md)
(collections-specific commands and test layout).

## Standing instructions

[`AGENTS.md`](AGENTS.md) at the repo root holds the non-negotiable rules
this build follows (report date is config, money is `Decimal`, never
drop a row silently, every failure is a typed error, docs updated in
the same commit as the behavior change). Read it before changing
anything under `backend/app/collections/`.

## Pull requests

Each PR follows the template: what it adds, which requirement it serves,
which docs were updated, verification commands run, and known gaps carried
to the next phase. Self-review before merge; run `/ponytail-review` on the
diff first.
