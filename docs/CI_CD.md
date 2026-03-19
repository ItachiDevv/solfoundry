# CI/CD Pipeline

Overview of the GitHub Actions workflows that power SolFoundry's continuous integration and deployment.

---

## Workflows

### 1. `ci.yml` — Continuous Integration

**Trigger:** every pull request to `main` or `develop`, and pushes to `main`.

| Job | What it does |
|-----|-------------|
| `frontend-lint` | Runs ESLint on TypeScript/React code |
| `frontend-typecheck` | `tsc --noEmit` to catch type errors |
| `frontend-test` | Vitest unit tests |
| `frontend-build` | Full production build (runs after lint + typecheck + tests pass) |
| `backend-lint` | Ruff linter + format check for Python |
| `backend-test` | pytest against `backend/tests/` |
| `contracts-check` | Clippy, rustfmt, and `cargo build` — **skipped** when `contracts/Cargo.toml` does not exist yet |

Caching:
- npm dependencies cached via `actions/setup-node` cache option.
- pip dependencies cached via `actions/setup-python` cache option.
- Rust dependencies cached via `Swatinem/rust-cache`.

### 2. `deploy.yml` — Deployment

**Trigger:** push to `main` only (i.e., after a PR is merged).

| Job | Target |
|-----|--------|
| `deploy-frontend` | Builds the Vite app then pushes to **Vercel** (production) |
| `deploy-backend` | Builds a Docker image, pushes to **GHCR**, then SSH-deploys to a **DigitalOcean** droplet |

Required secrets (set in repo Settings > Secrets):

| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Vercel personal access token |
| `VERCEL_ORG_ID` | Vercel organization / team ID |
| `VERCEL_PROJECT_ID` | Vercel project ID |
| `DO_HOST` | DigitalOcean droplet IP |
| `DO_USERNAME` | SSH user on the droplet |
| `DO_SSH_KEY` | Private SSH key for droplet access |

### 3. `anchor.yml` — Solana Contract Checks

**Trigger:** PRs and pushes that touch `contracts/**` or `Anchor.toml`.

Steps:
1. Installs Solana CLI + Anchor CLI.
2. Configures Solana for **devnet**.
3. `anchor build` — compiles all programs.
4. `anchor test --skip-local-validator` — runs on-chain tests against devnet.

### Existing Workflows (not modified)

| File | Purpose |
|------|---------|
| `pr-review.yml` | AI-powered code review |
| `bounty-tracker.yml` | Tracks merged PRs for bounty payouts |
| `claim-guard.yml` | Blocks duplicate Tier 1 claims |
| `wallet-check.yml` | Validates contributor wallet addresses |

---

## Branch Protection Rules

Recommended settings for the `main` branch (configure in **Settings > Branches > Branch protection rules**):

1. **Require a pull request before merging**
   - Require at least 1 approving review.
   - Dismiss stale pull request approvals when new commits are pushed.

2. **Require status checks to pass before merging**
   - Required checks:
     - `Frontend — Lint`
     - `Frontend — Type Check`
     - `Frontend — Tests`
     - `Frontend — Build`
     - `Backend — Lint (Ruff)`
     - `Backend — Tests (pytest)`
   - Require branches to be up-to-date before merging.

3. **Require conversation resolution before merging**

4. **Do not allow bypassing the above settings** (applies to admins too).

5. **Restrict force pushes** — nobody should force-push to `main`.

6. **Require linear history** — enforce squash or rebase merges only.

---

## Local Development Tips

```bash
# Run frontend checks locally
cd frontend
npm run lint
npx tsc --noEmit
npm run test

# Run backend checks locally
cd backend
pip install ruff pytest pytest-asyncio httpx
ruff check .
pytest tests/ -v
```
