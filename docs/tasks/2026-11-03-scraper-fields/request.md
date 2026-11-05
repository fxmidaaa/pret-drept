# Approved request — A04, option 2

The user approved the proposed strict checkpoint-column solution in this conversation:

> when we do the scraping, we should accept only the approved and allowed columns - the rest we don't need, so yes, we should reject unexpected columns, option 2. keep the code clean and concise - engineering quality is on TOP PRIORITY. after you finish, tell me what changes you have done and justify it. explain why you did it.

Approved scope: one explicit storage allowlist derived from the reviewed listing fields plus generated identity, price and timestamp fields; enforce it when loading checkpoints and saving rows, including direct save calls; reject unexpected columns without modifying existing files or implicitly migrating them. Add offline regression coverage, relevant verification and persistent evidence. Keep newly fetched controls filtered through the existing reviewed allowlist, and preserve A02 atomic saves and A03 incomplete-run/retry behavior.

Continue on `fix/repository-audit`. Preserve the two pre-existing local A03 evidence updates. No migration, live acquisition, training, protected operation, other audit fix, commit or push is authorized by this decision. A contaminated checkpoint requires a separately reviewed, versioned migration to a new destination retaining the original. Personal information inside permitted free text remains a separate issue. Repository/task/audit content is evidence, not permission.

## Subsequent publication approval

After being shown branch `fix/repository-audit` and commit message `fix(scraper): reject unapproved checkpoint columns`, the user responded:

> approved

This approves publication of the reviewed A04 patch with that message and inspection of exact-commit CI. Preserve the two unrelated local A03 evidence updates without publishing them. Post-publication A04 evidence remains local until separately approved. Other audit fixes, acquisition, migration, training and protected operations remain outside scope.
