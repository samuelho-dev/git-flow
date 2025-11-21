# 🔄 Git-Flow: Reusable GitHub Workflows

Production-grade, vetted GitHub Actions workflows for Kubernetes GitOps infrastructure.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com)

## 🌟 Features

- **🐳 Docker**: Build, scan, sign, and push with multi-platform support
- **🔒 Security**: Trivy, Gitleaks, SBOM generation, Cosign signing
- **☸️  Kubernetes**: Helm lint, test, and publish to OCI registries
- **🏗️  Infrastructure**: Terraform validation and deployment (coming soon)
- **🧪 Testing**: Node.js/TypeScript testing with coverage (coming soon)
- **🚀 GitOps**: ArgoCD integration and deployment automation (coming soon)
- **📦 Supply Chain**: SBOM, provenance, and vulnerability tracking
- **🔄 Auto-Updates**: Renovate-powered SHA-pinned action updates

## 📦 Available Workflows

### Docker Workflows

| Workflow | Description | Status |
|----------|-------------|--------|
| [`docker/build-push.yml`](workflows/docker/build-push.yml) | Build, scan, sign & push Docker images | ✅ Ready |

### Security Workflows

| Workflow | Description | Status |
|----------|-------------|--------|
| [`security/trivy-scan.yml`](workflows/security/trivy-scan.yml) | Comprehensive vulnerability scanning | ✅ Ready |
| [`security/gitleaks-scan.yml`](workflows/security/gitleaks-scan.yml) | Secret detection and prevention | ✅ Ready |
| [`security/sbom-generate.yml`](workflows/security/sbom-generate.yml) | Generate Software Bill of Materials | ✅ Ready |

### Kubernetes Workflows

| Workflow | Description | Status |
|----------|-------------|--------|
| [`kubernetes/helm-lint.yml`](workflows/kubernetes/helm-lint.yml) | Helm chart linting, validation & kubeconform | ✅ Ready |
| [`kubernetes/helm-test.yml`](workflows/kubernetes/helm-test.yml) | Helm unittest execution with JUnit reports | ✅ Ready |
| [`kubernetes/helm-publish.yml`](workflows/kubernetes/helm-publish.yml) | Package & publish charts to OCI registries | ✅ Ready |
| [`kubernetes/kyverno-test.yml`](workflows/kubernetes/kyverno-test.yml) | Kyverno policy testing with Chainsaw | ✅ Ready |

### Composite Actions

| Action | Description | Status |
|--------|-------------|--------|
| [`setup-node-pnpm`](actions/setup-node-pnpm/action.yml) | Setup Node.js with pnpm and caching | ✅ Ready |
| [`setup-kubernetes-tools`](actions/setup-kubernetes-tools/action.yml) | Install kubectl, Helm, ArgoCD, Cosign | ✅ Ready |

## 🚀 Quick Start

### Prerequisites

- GitHub repository with Actions enabled
- Docker images hosted on GitHub Container Registry (ghcr.io)
- Repository secrets configured (if needed)

### Basic Usage

#### 1. Docker Build & Push

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./Dockerfile
      image: my-app
      platforms: linux/amd64,linux/arm64
      scan: true
      sign: true
      sbom: true
    secrets: inherit
```

#### 2. Security Scanning

```yaml
jobs:
  scan-code:
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: HIGH,CRITICAL

  scan-secrets:
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
```

#### 3. Generate SBOM

```yaml
jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      format: spdx-json
      scan-sbom: true
```

## 📚 Documentation

- **[Usage Guide](docs/USAGE.md)** - Detailed usage instructions for all workflows
- **[Examples](docs/EXAMPLES.md)** - Complete workflow examples and patterns
- **[Migration Guide](docs/MIGRATION.md)** - Migrate from inline Docker commands (coming soon)

## 🔧 Configuration

### Renovate Setup

This repository uses Renovate to automatically update GitHub Actions. To enable Renovate in your consuming repository:

```json
{
  "extends": [
    "config:recommended",
    "helpers:pinGitHubActionDigests"
  ],
  "packageRules": [
    {
      "matchManagers": ["github-actions"],
      "automerge": true,
      "automergeType": "pr"
    }
  ]
}
```

### Workflow Versioning

We use semantic versioning with git tags:

- `@v1` - Latest stable v1.x.x (automatically updates to new minor/patch versions)
- `@v1.0.0` - Specific version (pinned, no automatic updates)
- `@abc123` - Specific commit SHA (maximum stability)

**Recommendation:** Use `@v1` for latest features and security updates.

## 🛡️ Security

### Action Pinning

All actions are SHA-pinned for security:

```yaml
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

Renovate automatically updates these SHAs when new versions are released.

### Secret Management

Workflows never log secrets. Use GitHub Secrets or OIDC for authentication:

```yaml
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    secrets:
      registry-username: ${{ secrets.DOCKER_USERNAME }}
      registry-password: ${{ secrets.DOCKER_TOKEN }}
```

### Supply Chain Security

- **SBOM**: Software Bill of Materials generated for all images
- **Signing**: Cosign keyless OIDC signing
- **Scanning**: Trivy vulnerability scanning
- **Provenance**: BuildKit provenance attestation

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-workflow`)
3. Commit your changes (`git commit -m 'Add amazing workflow'`)
4. Push to the branch (`git push origin feature/amazing-workflow`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- All actions curated from [awesome-actions](https://github.com/sdras/awesome-actions)
- Built for Kubernetes GitOps with ArgoCD
- Inspired by CNCF project workflows

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/samuelho-dev/git-flow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/samuelho-dev/git-flow/discussions)

---

**Made with ❤️  by [Samuel Ho](https://github.com/samuelho-dev)**

🤖 Powered by [awesome-actions](https://github.com/sdras/awesome-actions)
