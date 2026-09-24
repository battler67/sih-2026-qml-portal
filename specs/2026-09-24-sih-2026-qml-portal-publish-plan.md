# SIH 2026 QML Portal Publication Plan

## Goal

Publish the current consolidated portal as a clean snapshot in the existing public GitHub repository `battler67/sih-2026-qml-portal`, for judges to review.

## Plan

1. Confirm the GitHub repository exists, is public, and is empty.
2. Review the current checkout contents and ensure local credentials, Vercel metadata, generated artifacts, and local environments are excluded.
3. Prepare a clean snapshot from the current working tree, retaining the portal, backend, research architecture documents, setup material, and this publication plan; do not include the source checkout's prior commit history.
4. Create one initial commit and push it to the new repository's `main` branch.
5. Confirm the remote branch and published top-level content through GitHub.

## Scope and safeguards

- GitHub target: `https://github.com/battler67/sih-2026-qml-portal`.
- Do not change or connect any Vercel project or Git integration.
- Keep the source checkout and its existing remote/branch intact.
- Exclude `.git`, `.vercel`, `.env` files, local environments, dependency folders, and generated build/runtime artifacts according to `.gitignore`.
- No test or build commands are part of this publication request.

## Progress log

- 2026-09-24: Confirmed the target repository exists, is public, and is empty; confirmed the portal checkout has an existing remote to `battler67/quantum-helix-lab` and has uncommitted work. The new publication will use a clean snapshot so unrelated source history is not transferred.
