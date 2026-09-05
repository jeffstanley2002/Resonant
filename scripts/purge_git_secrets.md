# Purging Git Secrets

This repository starts without git history, so there is nothing to purge at initialization.

If a real secret is ever committed:
1. Revoke the exposed secret with the provider immediately.
2. Remove the secret from the working tree.
3. Use `git filter-repo` or BFG Repo-Cleaner to remove it from history.
4. Force-push only after coordinating with collaborators.
5. Rotate every credential that may have been exposed.
6. Run `python3 scripts/scan_secrets.py` before committing again.

Never rely on history rewriting alone. Treat committed credentials as compromised.

