# 📖 Usage Guide

Complete guide for using git-flow reusable workflows in your projects.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Docker Workflows](#docker-workflows)
3. [Security Workflows](#security-workflows)
4. [Kubernetes Workflows](#kubernetes-workflows)
5. [Infrastructure Workflows](#infrastructure-workflows)
6. [GitOps Workflows](#gitops-workflows)
7. [Composite Actions](#composite-actions)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

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

### `helm-lint.yml`

Lint and validate Helm charts with kubeconform and helm-docs verification.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `chart-path` | string | **required** | Path to Helm chart directory |
| `values-file` | string | `values.yaml` | Override values file |
| `strict` | boolean | `true` | Use strict linting (fail on warnings) |
| `kubeconform` | boolean | `true` | Run kubeconform validation |
| `kubernetes-version` | string | `1.30.0` | Kubernetes version for kubeconform |
| `helm-docs-check` | boolean | `true` | Check if README.md is up to date |
| `extra-values` | string | `''` | Additional values files (comma-separated) |
| `schema-validation` | boolean | `false` | Validate against JSON schemas |

#### Outputs

| Output | Description |
|--------|-------------|
| `lint-result` | Lint result (success/failure) |
| `chart-version` | Chart version from Chart.yaml |

#### Examples

**Basic Helm lint:**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
```

**Lint with schema validation:**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
      schema-validation: true
      extra-values: values-dev.yaml,values-prod.yaml
```

**Disable kubeconform:**
```yaml
jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
      kubeconform: false
      strict: false  # Allow warnings
```

---

### `helm-test.yml`

Run Helm unittest tests for chart validation.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `chart-path` | string | **required** | Path to Helm chart directory |
| `test-pattern` | string | `tests/*.yaml` | Test file pattern (glob) |
| `fail-fast` | boolean | `false` | Stop testing on first failure |
| `parallel` | boolean | `true` | Run tests in parallel |
| `output-format` | string | `junit` | Test output format (normal, junit, nunit) |
| `strict` | boolean | `true` | Fail on warnings |
| `update-snapshots` | boolean | `false` | Update test snapshots |

#### Outputs

| Output | Description |
|--------|-------------|
| `test-result` | Test result (success/failure) |
| `tests-run` | Number of tests executed |
| `tests-passed` | Number of tests passed |
| `tests-failed` | Number of tests failed |

#### Examples

**Basic Helm test:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/helm-test.yml@v1
    with:
      chart-path: charts/my-app
```

**Test with snapshot update:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/helm-test.yml@v1
    with:
      chart-path: charts/my-app
      update-snapshots: true
      output-format: junit
```

**Custom test pattern:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/helm-test.yml@v1
    with:
      chart-path: charts/my-app
      test-pattern: tests/**/*_test.yaml
      fail-fast: true
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

### `kyverno-test.yml`

Test Kyverno policies using Kyverno CLI and Chainsaw framework.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `policy-path` | string | **required** | Path to Kyverno policies directory |
| `test-path` | string | `tests` | Path to Chainsaw tests directory |
| `kyverno-version` | string | `v1.13.0` | Kyverno CLI version |
| `chainsaw-version` | string | `v0.2.14` | Chainsaw version |
| `test-framework` | string | `both` | Test framework (chainsaw, kyverno-cli, both) |
| `fail-fast` | boolean | `false` | Stop testing on first failure |
| `report-format` | string | `junit` | Report format (json, junit, none) |
| `validate-policies` | boolean | `true` | Validate policy syntax before testing |

#### Outputs

| Output | Description |
|--------|-------------|
| `test-result` | Test result (success/failure) |
| `tests-run` | Number of tests executed |
| `tests-passed` | Number of tests passed |
| `tests-failed` | Number of tests failed |

#### Examples

**Basic Kyverno test:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/kyverno-test.yml@v1
    with:
      policy-path: policies/
```

**Test with Chainsaw only:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/kyverno-test.yml@v1
    with:
      policy-path: policies/
      test-path: tests/chainsaw
      test-framework: chainsaw
      fail-fast: true
```

**Test with specific versions:**
```yaml
jobs:
  test:
    uses: samuelho-dev/git-flow/.github/workflows/kyverno-test.yml@v1
    with:
      policy-path: policies/
      kyverno-version: v1.13.0
      chainsaw-version: v0.2.14
      report-format: junit
```

---

## Infrastructure Workflows

### `terraform-validate.yml`

Validate Terraform configuration with formatting checks and security scanning.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `terraform-version` | string | `1.9.8` | Terraform version |
| `format-check` | boolean | `true` | Check Terraform formatting |
| `tfsec-scan` | boolean | `true` | Run tfsec security scan |
| `checkov-scan` | boolean | `true` | Run Checkov compliance scan |
| `terraform-docs-check` | boolean | `false` | Check if README.md is up to date |
| `upload-sarif` | boolean | `true` | Upload security results to GitHub Security |
| `working-directory` | string | `.` | Working directory for commands |

#### Outputs

| Output | Description |
|--------|-------------|
| `validation-result` | Validation result (success/failure) |
| `format-result` | Format check result |
| `security-findings` | Number of security findings |

#### Examples

**Basic Terraform validation:**
```yaml
jobs:
  validate:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-validate.yml@v1
    with:
      terraform-path: terraform/environments/prod
```

**Full validation with docs check:**
```yaml
jobs:
  validate:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-validate.yml@v1
    with:
      terraform-path: terraform/environments/prod
      format-check: true
      tfsec-scan: true
      checkov-scan: true
      terraform-docs-check: true
```

---

### `terraform-plan.yml`

Generate Terraform plan with cost estimation and PR comments.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `terraform-version` | string | `1.9.8` | Terraform version |
| `plan-args` | string | `''` | Additional arguments for terraform plan |
| `var-file` | string | `''` | Path to tfvars file (relative to terraform-path) |
| `working-directory` | string | `.` | Working directory for commands |
| `comment-pr` | boolean | `true` | Comment plan output on PR |
| `cost-estimation` | boolean | `false` | Run Infracost for cost estimation |
| `upload-plan` | boolean | `true` | Upload plan file as artifact |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `terraform-token` | No | Terraform Cloud/Enterprise API token |
| `aws-access-key-id` | No | AWS Access Key ID (if using AWS) |
| `aws-secret-access-key` | No | AWS Secret Access Key (if using AWS) |
| `infracost-api-key` | No | Infracost API key for cost estimation |

#### Outputs

| Output | Description |
|--------|-------------|
| `plan-result` | Plan result (success/failure) |
| `resources-to-add` | Number of resources to add |
| `resources-to-change` | Number of resources to change |
| `resources-to-destroy` | Number of resources to destroy |

#### Examples

**Basic Terraform plan:**
```yaml
jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
    secrets: inherit
```

**Plan with cost estimation:**
```yaml
jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
      cost-estimation: true
      var-file: prod.tfvars
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}
```

**Plan with AWS credentials:**
```yaml
jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/aws
      comment-pr: true
    secrets:
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

### `terraform-apply.yml`

Apply Terraform changes with state backup and approval gates.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `terraform-path` | string | **required** | Path to Terraform directory |
| `terraform-version` | string | `1.9.8` | Terraform version |
| `plan-artifact-name` | string | `''` | Name of plan artifact to apply |
| `apply-args` | string | `''` | Additional arguments for terraform apply |
| `working-directory` | string | `.` | Working directory for commands |
| `environment` | string | `''` | GitHub environment for approval |
| `backup-state` | boolean | `true` | Backup state file before apply |
| `skip-plan` | boolean | `false` | Skip plan validation (NOT RECOMMENDED) |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `terraform-token` | No | Terraform Cloud/Enterprise API token |
| `aws-access-key-id` | No | AWS Access Key ID (if using AWS) |
| `aws-secret-access-key` | No | AWS Secret Access Key (if using AWS) |

#### Outputs

| Output | Description |
|--------|-------------|
| `apply-result` | Apply result (success/failure) |
| `resources-applied` | Number of resources applied |

#### Examples

**Apply with plan artifact:**
```yaml
jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/environments/prod

  apply:
    needs: plan
    uses: samuelho-dev/git-flow/.github/workflows/terraform-apply.yml@v1
    with:
      terraform-path: terraform/environments/prod
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: production
    secrets: inherit
```

**Apply with environment approval:**
```yaml
jobs:
  apply:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-apply.yml@v1
    with:
      terraform-path: terraform/environments/prod
      environment: production  # Requires GitHub Environment approval
      backup-state: true
    secrets: inherit
```

---

## GitOps Workflows

### `gitops-update-manifests.yml`

Update Kubernetes manifests with new image tags or Helm values.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `manifest-path` | string | **required** | Path to manifests directory |
| `update-type` | string | `image` | Update type (image, helm-values, kustomize) |
| `image-name` | string | `''` | Image name to update (for image type) |
| `image-tag` | string | `''` | New image tag |
| `file-pattern` | string | `**/*.yaml` | File pattern to update (glob) |
| `helm-key` | string | `''` | Helm value key path (e.g., image.tag) |
| `helm-value` | string | `''` | Helm value to set |
| `commit-message` | string | `''` | Git commit message |
| `create-pr` | boolean | `false` | Create pull request instead of direct commit |
| `pr-branch` | string | `gitops/auto-update` | Branch name for PR |
| `target-branch` | string | `main` | Target branch for updates |

#### Outputs

| Output | Description |
|--------|-------------|
| `update-result` | Update result (success/failure) |
| `files-updated` | Number of files updated |
| `pr-url` | Pull request URL (if created) |

#### Examples

**Update image tag:**
```yaml
jobs:
  update:
    uses: samuelho-dev/git-flow/.github/workflows/gitops-update-manifests.yml@v1
    with:
      manifest-path: k8s/apps/my-app
      update-type: image
      image-name: ghcr.io/owner/my-app
      image-tag: v1.2.3
```

**Update with PR creation:**
```yaml
jobs:
  update:
    uses: samuelho-dev/git-flow/.github/workflows/gitops-update-manifests.yml@v1
    with:
      manifest-path: k8s/apps/my-app
      update-type: image
      image-name: ghcr.io/owner/my-app
      image-tag: ${{ github.sha }}
      create-pr: true
      pr-branch: gitops/update-${{ github.sha }}
```

**Update Helm values:**
```yaml
jobs:
  update:
    uses: samuelho-dev/git-flow/.github/workflows/gitops-update-manifests.yml@v1
    with:
      manifest-path: helm/my-app
      update-type: helm-values
      helm-key: image.tag
      helm-value: v1.2.3
      commit-message: "chore: update image tag to v1.2.3"
```

---

### `argocd-sync.yml`

Trigger ArgoCD application sync with health verification.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `argocd-server` | string | **required** | ArgoCD server URL |
| `argocd-app-name` | string | **required** | ArgoCD application name |
| `argocd-namespace` | string | `argocd` | ArgoCD namespace |
| `sync-strategy` | string | `auto` | Sync strategy (auto, apply, hook) |
| `prune` | boolean | `false` | Prune resources during sync |
| `force` | boolean | `false` | Force sync (override diverged state) |
| `dry-run` | boolean | `false` | Perform dry-run sync |
| `wait-for-sync` | boolean | `true` | Wait for sync to complete |
| `sync-timeout` | number | `300` | Sync timeout in seconds |
| `health-check` | boolean | `true` | Check application health after sync |
| `revision` | string | `''` | Target revision (branch, tag, commit) |

#### Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `argocd-token` | Yes | ArgoCD authentication token |
| `kubeconfig` | No | Kubernetes config (if accessing cluster directly) |

#### Outputs

| Output | Description |
|--------|-------------|
| `sync-result` | Sync result (success/failure) |
| `sync-status` | Sync status (Synced, OutOfSync, Unknown) |
| `health-status` | Health status (Healthy, Progressing, Degraded, Suspended) |

#### Examples

**Basic ArgoCD sync:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

**Sync with prune and force:**
```yaml
jobs:
  sync:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app
      prune: true
      force: true
      wait-for-sync: true
      sync-timeout: 600
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

**Dry-run sync:**
```yaml
jobs:
  sync-test:
    uses: samuelho-dev/git-flow/.github/workflows/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app
      dry-run: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
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
