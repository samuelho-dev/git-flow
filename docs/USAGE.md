# 📖 Usage Guide

Complete guide for using git-flow reusable workflows in your projects.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Docker Workflows](#docker-workflows)
3. [Security Workflows](#security-workflows)
4. [Kubernetes Workflows](#kubernetes-workflows)
5. [Infrastructure Workflows](#infrastructure-workflows)
6. [ECS Workflows](#ecs-workflows)
7. [GitOps Workflows](#gitops-workflows)
8. [Git Workflows](#git-workflows)
9. [Composite Actions](#composite-actions)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

**Required:**
- GitHub repository with Actions enabled
- Dockerfile in your repository (for Docker workflows)

**Recommended:**
- GitHub Container Registry access (ghcr.io)
- Repository secrets configured
- Renovate bot installed

### Basic Integration

1. Create `.github/workflows/` directory in your repository
2. Create a workflow file (e.g., `ci.yml`)
3. Reference git-flow workflows using `uses:`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
    with:
      image: my-app
    secrets: inherit
```

---

## Docker Workflows

### `docker-build-push.yml`

Build, scan, sign, and push Docker images with comprehensive security features.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `context` | string | `.` | Build context path |
| `dockerfile` | string | `./Dockerfile` | Path to Dockerfile |
| `image` | string | **required** | Image name (without registry/tag) |
| `registry` | string | `ghcr.io` | Container registry URL |
| `platforms` | string | `linux/amd64` | Target platforms (comma-separated) |
| `push` | boolean | `true` | Push image to registry |
| `scan` | boolean | `true` | Run Trivy vulnerability scan |
| `sign` | boolean | `true` | Sign image with Cosign |
| `sbom` | boolean | `true` | Generate SBOM |
| `cache-registry` | boolean | `true` | Use registry cache for faster builds |
| `build-args` | string | `''` | Build arguments (KEY=VALUE, one per line) |
| `severity` | string | `HIGH,CRITICAL` | Minimum vulnerability severity to report |
| `upload-sarif` | boolean | `true` | Upload scan results to GitHub Security |
| `cosign-identity-regexp` | string | `https://github.com/samuelho-dev/git-flow/.github/workflows/.*` | Cosign identity regexp for signature verification |
| `runs-on` | string | `homelab-runners` | Runner label to use |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `registry-username` | No | Registry username (defaults to `github.actor`) |
| `registry-password` | No | Registry password (defaults to `GITHUB_TOKEN`) |

#### Outputs

| Output | Description |
|--------|-------------|
| `digest` | Image digest (sha256:...) |
| `tags` | Image tags (newline-separated) |
| `sbom-path` | Path to SBOM artifact |

#### Complete Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:

permissions:
  contents: read
  packages: write
  id-token: write
  security-events: write

jobs:
  build-backend:
    name: Build Backend Image
    uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
    with:
      context: .
      dockerfile: ./docker/backend/Dockerfile
      image: my-app-backend
      registry: ghcr.io
      platforms: linux/amd64,linux/arm64
      scan: true
      sign: true
      sbom: true
      cache-registry: true
      build-args: |
        NODE_ENV=production
        APP_VERSION=${{ github.sha }}
      severity: HIGH,CRITICAL
    secrets:
      registry-username: ${{ github.actor }}
      registry-password: ${{ secrets.GITHUB_TOKEN }}

  build-frontend:
    name: Build Frontend Image
    uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
    with:
      dockerfile: ./docker/frontend/Dockerfile
      image: my-app-frontend
      platforms: linux/amd64
      scan: true
      sign: false  # Skip signing for frontend
      sbom: true
    secrets: inherit  # Inherit all secrets
```

#### Usage Notes

**Multi-platform builds:**
```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

**Custom build arguments:**
```yaml
build-args: |
  NODE_VERSION=20
  PNPM_VERSION=8
  BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
```

**Private registry:**
```yaml
registry: my-registry.com
secrets:
  registry-username: ${{ secrets.REGISTRY_USER }}
  registry-password: ${{ secrets.REGISTRY_TOKEN }}
```

**Skip features:**
```yaml
scan: false  # Skip vulnerability scanning
sign: false  # Skip image signing
sbom: false  # Skip SBOM generation
```

---

## Security Workflows

### `trivy-scan.yml`

Comprehensive vulnerability scanning for filesystems, images, repositories, and configurations.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `scan-type` | string | `fs` | Type of scan (fs, image, repo, config, sbom) |
| `scan-ref` | string | `.` | Target to scan |
| `severity` | string | `HIGH,CRITICAL` | Severity levels to report |
| `format` | string | `sarif` | Output format (sarif, json, table) |
| `exit-code` | string | `1` | Exit code when vulnerabilities found |
| `upload-sarif` | boolean | `true` | Upload results to GitHub Security |
| `skip-files` | string | `''` | Files to skip (comma-separated) |
| `skip-dirs` | string | `node_modules,dist,build,.git` | Directories to skip |
| `timeout` | string | `10m` | Scan timeout duration |

#### Examples

**Scan filesystem:**
```yaml
jobs:
  scan-code:
    uses: samuelho-dev/git-flow/.github/workflows/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: HIGH,CRITICAL
      skip-dirs: node_modules,dist,.git
```

**Scan Docker image:**
```yaml
jobs:
  scan-image:
    uses: samuelho-dev/git-flow/.github/workflows/trivy-scan.yml@v1
    with:
      scan-type: image
      scan-ref: ghcr.io/samuelho-dev/my-app:latest
      severity: CRITICAL
```

**Scan Kubernetes manifests:**
```yaml
jobs:
  scan-k8s:
    uses: samuelho-dev/git-flow/.github/workflows/trivy-scan.yml@v1
    with:
      scan-type: config
      scan-ref: deploy/kubernetes/
      format: table
```

---

### `gitleaks-scan.yml`

Secret detection and prevention with 160+ secret patterns.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `scan-path` | string | `.` | Path to scan for secrets |
| `config-path` | string | `''` | Path to gitleaks config file |
| `format` | string | `sarif` | Output format (sarif, json, csv) |
| `fail-on-findings` | boolean | `true` | Fail workflow if secrets found |
| `upload-sarif` | boolean | `true` | Upload results to GitHub Security |
| `baseline-path` | string | `''` | Path to baseline file (ignore known findings) |
| `log-level` | string | `info` | Log level (debug, info, warn, error) |

#### Examples

**Basic secret scan:**
```yaml
jobs:
  scan-secrets:
    uses: samuelho-dev/git-flow/.github/workflows/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
```

**With custom config:**
```yaml
jobs:
  scan-secrets:
    uses: samuelho-dev/git-flow/.github/workflows/gitleaks-scan.yml@v1
    with:
      config-path: .gitleaks.toml
      baseline-path: .gitleaks-baseline.json
      log-level: debug
```

**Scan specific path:**
```yaml
jobs:
  scan-src:
    uses: samuelho-dev/git-flow/.github/workflows/gitleaks-scan.yml@v1
    with:
      scan-path: src/
      fail-on-findings: false  # Report only
```

---

### `sbom-generate.yml`

Generate Software Bill of Materials (SBOM) for supply chain security.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `target-type` | string | `directory` | Target type (image, directory, file) |
| `target` | string | `.` | Target to scan |
| `format` | string | `spdx-json` | SBOM format (spdx-json, cyclonedx-json) |
| `output-file` | string | `sbom.spdx.json` | Output file name |
| `upload-artifact` | boolean | `true` | Upload SBOM as artifact |
| `upload-dependency-snapshot` | boolean | `true` | Upload to GitHub Dependency Graph |
| `scan-sbom` | boolean | `true` | Scan SBOM for vulnerabilities |

#### Examples

**Generate SBOM for directory:**
```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      format: spdx-json
```

**Generate SBOM for Docker image:**
```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/sbom-generate.yml@v1
    with:
      target-type: image
      target: ghcr.io/samuelho-dev/my-app:latest
      scan-sbom: true
```

**CycloneDX format:**
```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/sbom-generate.yml@v1
    with:
      format: cyclonedx-json
      output-file: sbom.cdx.json
```

---

## Kubernetes Workflows


---


---

### `helm-lint.yml`

Lint and validate Helm charts with optional per-values-file runs, dependency build, and kubeconform schema validation.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `chart-path` | string | **required** | Path to Helm chart directory |
| `values-files` | string | `''` | Newline-separated list of values files to lint against (one `helm lint` run per file) |
| `helm-version` | string | `v3.16.3` | Helm version to use |
| `lint-strict` | boolean | `true` | Fail on warnings (`--strict`) |
| `build-dependencies` | boolean | `true` | Run `helm dependency build` before linting |
| `oci-registry` | string | `ghcr.io` | OCI registry for dependency pull |
| `kubeconform` | boolean | `true` | Pipe `helm template` output through kubeconform |
| `kubernetes-version` | string | `master` | Kubernetes schema version for kubeconform |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `registry-username` | No | Registry username for private OCI chart dependencies |
| `registry-password` | No | Registry password for private OCI chart dependencies |

#### Outputs

| Output | Description |
|--------|-------------|
| `result` | Lint result (success/failure) |

#### Examples

**Basic Helm lint:**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
```

**Lint against multiple values files:**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
      values-files: |
        values-dev.yaml
        values-prod.yaml
```

**Disable kubeconform (e.g. CRD-heavy chart):**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
      kubeconform: false
      lint-strict: false
```

---

### `helm-publish.yml`

Package and publish Helm charts to OCI registries with signing.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `chart-path` | string | **required** | Path to Helm chart directory |
| `registry` | string | `ghcr.io` | OCI registry URL |
| `repository` | string | `{owner}/charts` | Chart repository path |
| `sign-chart` | boolean | `true` | Sign chart with Cosign |
| `create-release` | boolean | `true` | Create GitHub release |
| `multi-registry` | string | `''` | Additional registries (comma-separated) |
| `update-index` | boolean | `false` | Update Helm repository index |
| `provenance` | boolean | `true` | Generate chart provenance file |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `registry-username` | No | Registry username (defaults to `github.actor`) |
| `registry-password` | No | Registry password (defaults to `GITHUB_TOKEN`) |
| `gpg-private-key` | No | GPG private key for chart signing |
| `gpg-passphrase` | No | GPG key passphrase |

#### Outputs

| Output | Description |
|--------|-------------|
| `chart-version` | Published chart version |
| `chart-digest` | OCI digest of published chart |
| `release-url` | GitHub release URL |

#### Examples

**Basic Helm publish:**
```yaml
jobs:
  publish:
    uses: samuelho-dev/git-flow/.github/workflows/helm-publish.yml@v1
    with:
      chart-path: charts/my-app
    secrets: inherit
```

**Publish to multiple registries:**
```yaml
jobs:
  publish:
    uses: samuelho-dev/git-flow/.github/workflows/helm-publish.yml@v1
    with:
      chart-path: charts/my-app
      multi-registry: docker.io,quay.io
      sign-chart: true
    secrets: inherit
```

**Publish without GitHub release:**
```yaml
jobs:
  publish:
    uses: samuelho-dev/git-flow/.github/workflows/helm-publish.yml@v1
    with:
      chart-path: charts/my-app
      create-release: false
      provenance: false
```

---


---

## Infrastructure Workflows

### `terraform-validate.yml`

Validate Terraform configuration with formatting checks and security scanning. Runs on `ubuntu-latest` with no cloud credentials required.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `terraform-version` | string | `latest` | Terraform version |
| `format-check` | boolean | `true` | Check Terraform formatting (`terraform fmt -check`) |
| `security-scan` | boolean | `true` | Run security scanning |
| `severity` | string | `HIGH,CRITICAL` | Minimum severity to flag |

#### Outputs

| Output | Description |
|--------|-------------|
| `result` | Validation result (success/failure) |

#### Examples

**Basic Terraform validation:**
```yaml
jobs:
  validate:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-validate.yml@v1
    with:
      terraform-path: terraform/environments/prod
```

**Validation with security scan disabled:**
```yaml
jobs:
  validate:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-validate.yml@v1
    with:
      terraform-path: terraform/environments/prod
      security-scan: false
```

---

### `terraform-plan.yml`

Generate a Terraform plan and post a summary comment on the PR. Uses GitHub OIDC (`id-token: write`) for AWS authentication — no static credentials required.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `terraform-version` | string | `latest` | Terraform version |
| `var-file` | string | `''` | Path to tfvars file (relative to terraform-path) |
| `aws-region` | string | `us-west-2` | AWS region |
| `plan-artifact-name` | string | `tfplan` | Name for the uploaded plan artifact |
| `post-pr-comment` | boolean | `true` | Comment plan summary on PR |
| `cost-estimation` | boolean | `false` | Run Infracost cost estimation |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `aws-role-arn` | No | AWS IAM role ARN for OIDC assumption |
| `infracost-api-key` | No | Infracost API key for cost estimation |

#### Outputs

| Output | Description |
|--------|-------------|
| `has-changes` | `true` if the plan contains infrastructure changes |
| `plan-artifact-name` | Name of the uploaded plan artifact |

#### Examples

**Basic Terraform plan:**
```yaml
permissions:
  id-token: write
  pull-requests: write

jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

**Plan with cost estimation:**
```yaml
permissions:
  id-token: write
  pull-requests: write

jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
      cost-estimation: true
      var-file: prod.tfvars
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
      infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}
```

---

### `terraform-apply.yml`

Download the plan artifact produced by `terraform-plan.yml` and apply it. Pair with a GitHub `environment` for a required-reviewer approval gate before production applies.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `plan-artifact-name` | string | **required** | Name of the plan artifact to download and apply |
| `terraform-version` | string | `latest` | Terraform version |
| `aws-region` | string | `us-west-2` | AWS region |
| `environment` | string | `''` | GitHub environment name for approval gate |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `aws-role-arn` | Yes | AWS IAM role ARN for OIDC assumption |

#### Outputs

| Output | Description |
|--------|-------------|
| `applied` | `true` if the apply completed successfully |

#### Examples

**Plan then apply with production approval gate:**
```yaml
permissions:
  id-token: write

jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}

  apply:
    needs: plan
    uses: samuelho-dev/git-flow/.github/workflows/terraform-apply.yml@v1
    with:
      terraform-path: terraform/environments/prod
      plan-artifact-name: ${{ needs.plan.outputs.plan-artifact-name }}
      environment: production
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

---

## ECS Workflows

### `ecs-deploy.yml`

Deploy a service to AWS ECS Express Mode via GitHub OIDC. No static credentials required.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `service-name` | string | **required** | ECS service name |
| `image` | string | **required** | Full image URI to deploy (e.g. `ghcr.io/org/app:sha-abc`) |
| `execution-role-arn` | string | **required** | ECS task execution role ARN |
| `infrastructure-role-arn` | string | **required** | IAM role ARN for ECS infrastructure operations |
| `aws-region` | string | `us-west-2` | AWS region |
| `environment` | string | `''` | GitHub environment name for approval gate |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `aws-role-arn` | Yes | AWS IAM role ARN for OIDC assumption |

#### Outputs

| Output | Description |
|--------|-------------|
| `image` | The image URI that was deployed |

#### Examples

**Deploy to ECS after image build:**
```yaml
permissions:
  id-token: write

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
    with:
      image: my-app
      push: true
    secrets: inherit

  deploy:
    needs: build
    uses: samuelho-dev/git-flow/.github/workflows/ecs-deploy.yml@v1
    with:
      service-name: my-app-prod
      image: ${{ needs.build.outputs.tags }}
      execution-role-arn: ${{ vars.ECS_EXECUTION_ROLE_ARN }}
      infrastructure-role-arn: ${{ vars.ECS_INFRA_ROLE_ARN }}
      environment: production
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

---

### `ecs-smoke.yml`

Poll a JSON `/health` endpoint until the service is healthy. Set `soak-passes: 1` for a first-success smoke test; set `soak-passes: N` for an N-consecutive-probe soak gate.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | **required** | Base URL of the deployed service |
| `path` | string | `/health` | Health check path |
| `expected-version` | string | `''` | Version string to match in the health response (optional) |
| `accept-status` | string | `ok,degraded` | Comma-separated health statuses to accept as passing |
| `expected-http` | number | `200` | Expected HTTP status code |
| `retries` | number | `20` | Maximum probe attempts before failing |
| `interval-seconds` | number | `15` | Seconds between probes |
| `soak-passes` | number | `1` | Consecutive passing probes required (`1` = first-success smoke) |

#### Outputs

| Output | Description |
|--------|-------------|
| `ok` | `true` if the health check passed |
| `version` | Version reported by the health endpoint |

#### Examples

**Smoke test after ECS deploy:**
```yaml
jobs:
  deploy:
    uses: samuelho-dev/git-flow/.github/workflows/ecs-deploy.yml@v1
    with:
      service-name: my-app-prod
      image: ghcr.io/org/my-app:sha-${{ github.sha }}
      execution-role-arn: ${{ vars.ECS_EXECUTION_ROLE_ARN }}
      infrastructure-role-arn: ${{ vars.ECS_INFRA_ROLE_ARN }}
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}

  smoke:
    needs: deploy
    uses: samuelho-dev/git-flow/.github/workflows/ecs-smoke.yml@v1
    with:
      url: https://my-app.example.com
      expected-version: ${{ github.sha }}
      retries: 20
      interval-seconds: 15
```

**Soak gate (5 consecutive passes):**
```yaml
jobs:
  soak:
    uses: samuelho-dev/git-flow/.github/workflows/ecs-smoke.yml@v1
    with:
      url: https://my-app.example.com
      soak-passes: 5
      interval-seconds: 30
```

---

## GitOps Workflows


---

### `argocd-sync.yml`

Wait for an ArgoCD application to reach Synced + Healthy status. Optionally triggers a sync first (`sync: true`). Use `resources` to scope the wait to specific resource kinds.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `app-name` | string | **required** | ArgoCD application name |
| `argocd-server` | string | **required** | ArgoCD server hostname (without protocol) |
| `resources` | string | `''` | Newline-separated list of `group:Kind:name` to scope the health wait |
| `sync` | boolean | `false` | Trigger a sync before waiting (otherwise waits for existing sync) |
| `sync-timeout` | number | `300` | Seconds to wait for sync to complete |
| `health-timeout` | number | `300` | Seconds to wait for healthy status |
| `plaintext` | boolean | `true` | Use plaintext (non-TLS) connection to ArgoCD server |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `argocd-token` | Yes | ArgoCD authentication token |

#### Outputs

| Output | Description |
|--------|-------------|
| `result` | Sync result (Synced/Healthy or failure reason) |

#### Examples

**Wait for app to be Synced+Healthy (ArgoCD auto-sync handles the commit):**
```yaml
jobs:
  wait:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      app-name: my-app
      argocd-server: argocd.example.com
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

**Trigger sync and wait:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      app-name: my-app
      argocd-server: argocd.example.com
      sync: true
      sync-timeout: 600
      health-timeout: 300
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

**Scope wait to specific resources:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      app-name: my-app
      argocd-server: argocd.example.com
      sync: true
      resources: |
        apps:Deployment:my-app
        :Service:my-app
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

---

## Git Workflows

### `sync-main-to-dev.yml`

Keep a target branch (e.g. `dev`) in sync with a source branch (e.g. `main`). The workflow tries the cleanest merge strategy first and escalates only when needed:

1. **Fast-forward** — no merge commit noise
2. **Merge commit** — when target has diverged
3. **Open a PR** — when there are merge conflicts that require human resolution

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `source-branch` | string | `main` | Branch to sync from |
| `target-branch` | string | `dev` | Branch to sync to |
| `create-pr-on-conflict` | boolean | `true` | Open a PR if merge conflicts prevent automatic sync |
| `pr-labels` | string | `automated,sync` | Comma-separated labels for conflict PRs |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `token` | No | GitHub token with repo write access (falls back to `GITHUB_TOKEN`) |

#### Outputs

| Output | Description |
|--------|-------------|
| `result` | Sync result: `fast-forward`, `merged`, `pr-created`, `up-to-date`, or `failed` |
| `pr-number` | PR number if a conflict PR was created |

#### Examples

**Basic — sync main to dev on every push:**
```yaml
name: Sync main to dev

on:
  push:
    branches: [main]

jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/sync-main-to-dev.yml@v1
    permissions:
      contents: write
      pull-requests: write
```

**Custom branches:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/sync-main-to-dev.yml@v1
    with:
      source-branch: release
      target-branch: develop
    permissions:
      contents: write
      pull-requests: write
```

**With a PAT for protected branches:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/sync-main-to-dev.yml@v1
    permissions:
      contents: write
      pull-requests: write
    secrets:
      token: ${{ secrets.SYNC_PAT }}
```

**Disable PR creation on conflict:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/sync-main-to-dev.yml@v1
    with:
      create-pr-on-conflict: false
    permissions:
      contents: write
      pull-requests: write
```

**Act on the result in a downstream job:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/sync-main-to-dev.yml@v1
    permissions:
      contents: write
      pull-requests: write

  notify:
    needs: sync
    if: needs.sync.outputs.result == 'pr-created'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Conflict PR #${{ needs.sync.outputs.pr-number }} needs review"
```

---

## Composite Actions

### `setup-node-pnpm`

Setup Node.js with pnpm and intelligent dependency caching.

#### Usage

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js with pnpm
        uses: samuelho-dev/git-flow/actions/setup-node-pnpm@v1
        with:
          node-version: 20
          pnpm-version: 8
          cache: true

      - name: Build
        run: pnpm build

      - name: Test
        run: pnpm test
```

#### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `node-version` | `20` | Node.js version |
| `pnpm-version` | `8` | pnpm version |
| `cache` | `true` | Enable caching |
| `working-directory` | `.` | Working directory |

#### Outputs

| Output | Description |
|--------|-------------|
| `cache-hit` | Whether cache was restored |
| `pnpm-store-path` | pnpm store directory path |

---

### `setup-kubernetes-tools`

Install kubectl, Helm, ArgoCD CLI, and Cosign.

#### Usage

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Kubernetes tools
        uses: samuelho-dev/git-flow/actions/setup-kubernetes-tools@v1
        with:
          install-kubectl: true
          install-helm: true
          install-argocd: true
          install-cosign: true
          kubectl-version: v1.30.0
          helm-version: v3.16.3

      - name: Deploy with Helm
        run: helm upgrade --install my-app ./chart
```

#### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `kubectl-version` | `v1.30.0` | kubectl version |
| `helm-version` | `v3.16.3` | Helm version |
| `argocd-version` | `v2.10.20` | ArgoCD CLI version |
| `cosign-version` | `v2.4.1` | Cosign version |
| `install-kubectl` | `true` | Install kubectl |
| `install-helm` | `true` | Install Helm |
| `install-argocd` | `false` | Install ArgoCD CLI |
| `install-cosign` | `false` | Install Cosign |

---

## Best Practices

### 1. Version Pinning

**Use major version tags for auto-updates:**
```yaml
uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
```

**Pin to specific version for stability:**
```yaml
uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1.0.0
```

**Use commit SHA for maximum security:**
```yaml
uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@abc123def456
```

### 2. Secret Management

**Use repository secrets:**
```yaml
secrets:
  registry-password: ${{ secrets.GITHUB_TOKEN }}
```

**Use `secrets: inherit` when appropriate:**
```yaml
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/workflows/docker-build-push.yml@v1
    secrets: inherit  # Pass all secrets
```

### 3. Permissions

**Grant minimal required permissions:**
```yaml
permissions:
  contents: read        # Read repository
  packages: write       # Push Docker images
  id-token: write       # Cosign signing
  security-events: write  # Upload scan results
```

### 4. Workflow Triggers

**Use path filters to skip unnecessary runs:**
```yaml
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'
      - '.github/workflows/**'
```

**Use concurrency to cancel outdated runs:**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

---

## Troubleshooting

### Build Failures

**Image push fails:**
```
Error: denied: permission denied
```

**Solution:** Ensure `packages: write` permission is granted and registry credentials are correct.

### Scan Failures

**Trivy scan timeout:**
```
Error: context deadline exceeded
```

**Solution:** Increase timeout:
```yaml
with:
  timeout: 15m
```

### Cache Issues

**Cache not restoring:**

**Solution:** Check cache key and ensure dependencies haven't changed:
```yaml
with:
  cache-registry: false  # Disable registry cache
```

---

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/samuelho-dev/git-flow/issues)
- **Examples**: [docs/EXAMPLES.md](EXAMPLES.md)
- **Discussions**: [GitHub Discussions](https://github.com/samuelho-dev/git-flow/discussions)
