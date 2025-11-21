# 📖 Usage Guide

Complete guide for using git-flow reusable workflows in your projects.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Docker Workflows](#docker-workflows)
3. [Security Workflows](#security-workflows)
4. [Composite Actions](#composite-actions)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

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
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app
    secrets: inherit
```

---

## Docker Workflows

### `docker/build-push.yml`

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
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
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
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
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

### `security/trivy-scan.yml`

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
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
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
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: image
      scan-ref: ghcr.io/samuelho-dev/my-app:latest
      severity: CRITICAL
```

**Scan Kubernetes manifests:**
```yaml
jobs:
  scan-k8s:
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: config
      scan-ref: deploy/kubernetes/
      format: table
```

---

### `security/gitleaks-scan.yml`

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
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
```

**With custom config:**
```yaml
jobs:
  scan-secrets:
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      config-path: .gitleaks.toml
      baseline-path: .gitleaks-baseline.json
      log-level: debug
```

**Scan specific path:**
```yaml
jobs:
  scan-src:
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      scan-path: src/
      fail-on-findings: false  # Report only
```

---

### `security/sbom-generate.yml`

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
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      format: spdx-json
```

**Generate SBOM for Docker image:**
```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: image
      target: ghcr.io/samuelho-dev/my-app:latest
      scan-sbom: true
```

**CycloneDX format:**
```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      format: cyclonedx-json
      output-file: sbom.cdx.json
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
uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
```

**Pin to specific version for stability:**
```yaml
uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1.0.0
```

**Use commit SHA for maximum security:**
```yaml
uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@abc123def456
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
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
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
