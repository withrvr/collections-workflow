# Standing instructions

- Report date is config, never `datetime.now()`.
- Money is `Decimal`, never `float`.
- Never drop a row silently. Every exclusion emits an exception with a rule code.
- The LLM never computes, chooses, or corrects a number. It narrates and explains.
- anydoc output is LLM context only, never a calculation source.
- Every user-facing failure is a typed error with a plain-English message.
- Update the owning doc in the same commit as the behaviour change.
- One logical change per commit, Conventional Commits format.
- Run `/ponytail-review` before opening any MR.
