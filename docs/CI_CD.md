# CI/CD Pipeline

This document describes the GitHub Actions CI/CD pipeline for the SolFoundry monorepo.

## Overview

The pipeline consists of three workflow files:

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `ci.yml` | PRs + push to main | Lint, type-check, test, build |
| **Deploy** | `deploy.yml` | Push to main | Deploy frontend + backend |
| **Anchor** | `anchor.yml` | Changes to `contracts/` | Build + test Solana programs |

## Workflow Details

### `ci.yml` -- Continuous Integration

Runs on every pull request to `main`/`develop` and on pushes to `main`.

**Frontend job:**
1. Install Node 20 dependencies
2. Lint with ESLint (gracefully skips if lint script is not defined)
3. Type-check with `tsc --noEmit`
4. Run Vitest unit tests
5. Production build

**Backend job:**
1. Install Python 3.12 dependencies + dev tools (Ruff, pytest)
2. Lint with Ruff
3. Check formatting with Ruff
4. Run pytest

**Contracts job (conditional):**
- Only runs when `contracts/Cargo.toml` exists
- Clippy lint, rustfmt check, release build
- Currently skipped since contracts are not yet implemented

### `deploy.yml` -- Deployment

Runs on push to `main` (i.e., after a PR merge).

**Both jobs are conditional** -- they only run when the `DEPLOY_ENABLED` repository variable is set to `true` (Settings > Secrets and variables > Actions > Variables). During early development, these jobs are skipped automatically.

- **Frontend -> Vercel:** Builds the Vite app and deploys via Vercel CLI
- **Backend -> DigitalOcean:** Builds Docker image, pushes to GHCR, deploys via SSH

### `anchor.yml` -- Solana Contract Checks

Only triggered by changes to `contracts/**` or `Anchor.toml`.

1. Installs Solana CLI + Anchor CLI
2. Configures Solana for devnet
3. Runs `anchor build` to compile programs
4. Runs `anchor test` against devnet

## Required Secrets

Configure these in **Settings > Secrets and variables > Actions** when ready to deploy:

| Secret | Required for | Description |
|--------|-------------|-------------|
| `VERCEL_TOKEN` | Frontend deploy | Vercel personal access token |
| `VERCEL_ORG_ID` | Frontend deploy | Vercel organization ID |
| `VERCEL_PROJECT_ID` | Frontend deploy | Vercel project ID |
| `DO_HOST` | Backend deploy | DigitalOcean droplet IP address |
| `DO_USERNAME` | Backend deploy | SSH username on the droplet |
| `DO_SSH_KEY` | Backend deploy | Private SSH key for droplet access |

Also create a **repository variable** (not a secret):

| Variable | Value | Purpose |
|----------|-------|---------|
| `DEPLOY_ENABLED` | `true` | Enables deploy.yml jobs. Omit or set to any other value to skip. |

> **Note:** `GITHUB_TOKEN` is provided automatically by GitHub Actions -- no configuration needed.

## Existing Workflows

These workflows were already in the repository and are not modified by this PR:

| File | Purpose |
|------|---------|
| `pr-review.yml` | AI-powered code review on PRs |
| `bounty-tracker.yml` | Tracks merged PRs for bounty payouts |
| `claim-guard.yml` | Prevents duplicate Tier 1 bounty claims |
| `wallet-check.yml` | Validates contributor wallet addresses |

## Branch Protection Rules

Recommended settings for the `main` branch (**Settings > Branches > Add rule**):

1. **Require pull request reviews** -- at least 1 approving review
2. **Require status checks to pass:**
   - `Frontend`
   - `Backend`
3. **Require conversation resolution before merging**
4. **Restrict force pushes** to `main`
5. **Require linear history** (squash or rebase merges only)

## Local Development

Run the same checks locally before pushing:

```bash
# Frontend
cd frontend
npm install
npx tsc --noEmit
npm run test
npm run build

# Backend
cd backend
pip install -r requirements.txt
pip install ruff pytest pytest-asyncio httpx
ruff check .
ruff format --check .
pytest tests/ -v
```

## Validating Workflows

GitHub Actions workflow YAML cannot be unit-tested directly. To validate correctness:

1. **YAML syntax:** Use [actionlint](https://github.com/rhysd/actionlint) locally:
   ```bash
   # macOS
   brew install actionlint
   # Run against all workflows
   actionlint .github/workflows/*.yml
   ```
2. **Validation script:** Run the included validation script:
   ```bash
   bash scripts/validate-workflows.sh
   ```
3. **Dry run:** Push to a feature branch and open a PR to trigger CI.
4. **Local execution:** Use [nektos/act](https://github.com/nektos/act) to run workflows locally in Docker.
