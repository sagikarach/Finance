---
name: push-finance
description: Push commits to the sagikarach/Finance repo. Use whenever the user asks to push this repo, or when a plain `git push` fails with "Permission to sagikarach/Finance.git denied to KarachSagi". Routes the push through the sagikarach gh HTTPS token because the SSH keys authenticate as the wrong account.
---

# Pushing the Finance repo

## The problem
This repo's `origin` is SSH via a host alias: `git@github-second:sagikarach/Finance.git`.
But **both** local SSH keys (`~/.ssh/id_ed25519` and `~/.ssh/id_ed25519_second`)
authenticate to GitHub as the **`KarachSagi`** account, which does **not** have write
access to `sagikarach/Finance`. So a plain `git push` fails with:

```
ERROR: Permission to sagikarach/Finance.git denied to KarachSagi.
```

The `gh` CLI, however, is logged into the **`sagikarach`** account over HTTPS with
`repo` scope — that token can push.

## The fix (one-off push, restores state afterward)
Commit normally, then push by temporarily activating the `sagikarach` gh account and
pushing over an explicit HTTPS URL (this does NOT change the `origin` remote). The gh
credential helper is forced as the only helper so the osxkeychain entry for `KarachSagi`
doesn't shadow it. Finally, restore the previously active gh account.

```bash
# 1. Commit as usual on main
git add <files>
git commit -m "..."

# 2. Push via the sagikarach token, then restore the active gh account
gh auth switch --user sagikarach && \
git -c credential.helper='!/opt/homebrew/bin/gh auth git-credential' \
    push https://github.com/sagikarach/Finance.git HEAD:main 2>&1; \
PUSH_RC=$?; \
gh auth switch --user KarachSagi >/dev/null 2>&1; \
exit $PUSH_RC
```

Notes:
- `HEAD:main` pushes the current branch to `main`. Adjust the target branch if needed.
- Always restore the active gh account (`gh auth switch --user KarachSagi`) even if the
  push fails, so the user's default account state is unchanged.
- Do NOT embed the token directly in a command (avoids leaking it into shell history).

## Permanent fix (offer it, don't apply without asking)
To make plain `git push` work, the user can either:
- Add the `id_ed25519_second` public key to the **`sagikarach`** GitHub account, or
- Switch `origin` to HTTPS: `git remote set-url origin https://github.com/sagikarach/Finance.git`
  (then keep `sagikarach` as the active gh account when pushing).
