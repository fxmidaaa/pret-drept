# Approved request — A02, option 1

The user approved the proposed A02 correction with:

> approved.

The approved proposal repairs checkpoint handling in the existing scraper: reject incompatible files before collection, validate checkpoint state, save through a temporary file with atomic replacement, add offline preservation/failure tests, and update instructions and task evidence. Preserve the original during any separately authorized migration.

Maintain the frozen architecture and legacy application interfaces; prefer small direct fixes over new infrastructure. A03 retry semantics and A04 resumed-field policy remain separate decisions. Dataset migration, live collection, training, protected operations, commit/push and other audit fixes are not authorized by this approval. Before any push, present branch `fix/repository-audit` and the proposed commit message for user approval.

## Publication approval

After being shown branch `fix/repository-audit` and commit message `fix(scraper): preserve checkpoints with validated atomic saves`, the user instructed:

> push

This authorizes committing/pushing the reviewed A02 patch and checking its resulting GitHub validation. Earlier A01 evidence updates remain separate local work; acquisition, migration and other fixes still require their own approval.
