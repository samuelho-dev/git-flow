# 🔄 Migration Guide

Comprehensive guide for migrating from inline GitHub Actions commands to git-flow reusable workflows.

## Table of Contents

1. [Why Migrate?](#why-migrate)
2. [Migration Strategy](#migration-strategy)
3. [Docker Workflows](#docker-workflows)
4. [Security Workflows](#security-workflows)
5. [Kubernetes/Helm Workflows](#kuberneteshelm-workflows)
6. [Terraform Workflows](#terraform-workflows)
7. [Common Migration Patterns](#common-migration-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Why Migrate?

### Benefits of Reusable Workflows

**Before (Inline Commands):**
- ❌ Duplicate code across multiple repositories
- ❌ Manual action version updates (security risk)
- ❌ Inconsistent security scanning practices
- ❌ No centralized workflow improvements
- ❌ Difficult to enforce organizational standards

**After (Reusable Workflows):**
- ✅ Single source of truth for CI/CD patterns
- ✅ Automatic action updates via Renovate
- ✅ Consistent security practices across all repos
- ✅ Centralized improvements benefit all consumers
- ✅ Enforced organizational standards
- ✅ Reduced maintenance burden (update once, benefit everywhere)

### Migration Effort

| Workflow Type | Effort | Time Estimate |
|---------------|--------|---------------|
| Docker | Low | 15-30 minutes |
| Security | Low | 10-20 minutes |
| Kubernetes/Helm | Medium | 30-60 minutes |
| Terraform | Medium | 45-90 minutes |

---

## Migration Strategy

### Step-by-Step Approach

1. **Identify**: Audit existing workflows and identify migration candidates
2. **Prioritize**: Start with high-value, low-risk workflows (Docker, Security)
3. **Test**: Create PR with reusable workflow, test thoroughly
4. **Deploy**: Merge PR after validation
5. **Monitor**: Watch first few runs for issues
6. **Iterate**: Move to next workflow

### Risk Mitigation

- **Run in parallel**: Keep old workflow temporarily, run both side-by-side
- **Feature flags**: Use workflow_dispatch to test before enabling on push/PR
- **Rollback plan**: Keep old workflow committed but disabled for quick rollback
- **Gradual rollout**: Migrate one repository at a time, not all at once

---

## Docker Workflows

### Migrate: Simple Docker Build

**Before (Inline Commands):**

```yaml
name: Build Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

**After (Reusable Workflow):**

```yaml
name: Build Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
      push: true
    secrets: inherit
```

**Savings:** 30 lines → 10 lines (67% reduction)

---

### Migrate: Docker Build with Security Scanning

**Before (Inline Commands):**

```yaml
name: Build and Scan

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Sign image
        run: |
          cosign sign --yes ghcr.io/${{ github.repository }}:${{ github.sha }}
```

**After (Reusable Workflow):**

```yaml
name: Build and Scan

on:
  push:
    branches: [main]

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
      push: true
      scan: true      # Trivy scanning
      sign: true      # Cosign signing
      sbom: true      # SBOM generation
    secrets: inherit
```

**Savings:** 45 lines → 13 lines (71% reduction)

---

### Migrate: Multi-Platform Docker Build

**Before (Inline Commands):**

```yaml
name: Multi-Platform Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64,linux/arm/v7
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
          cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max
```

**After (Reusable Workflow):**

```yaml
name: Multi-Platform Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
      platforms: linux/amd64,linux/arm64,linux/arm/v7
      push: true
      cache-registry: true
    secrets: inherit
```

**Savings:** 40 lines → 12 lines (70% reduction)

---

## Security Workflows

### Migrate: Trivy Vulnerability Scanning

**Before (Inline Commands):**

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'HIGH,CRITICAL'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

**After (Reusable Workflow):**

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'

jobs:
  scan:
    uses: samuelho-dev/git-flow/.github/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: HIGH,CRITICAL
```

**Savings:** 25 lines → 10 lines (60% reduction)

---

### Migrate: Secret Scanning with Gitleaks

**Before (Inline Commands):**

```yaml
name: Secret Scan

on:
  push:
  pull_request:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
```

**After (Reusable Workflow):**

```yaml
name: Secret Scan

on:
  push:
  pull_request:

jobs:
  scan:
    uses: samuelho-dev/git-flow/.github/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
```

**Savings:** 18 lines → 8 lines (56% reduction)

---

### Migrate: SBOM Generation

**Before (Inline Commands):**

```yaml
name: Generate SBOM

on:
  push:
    branches: [main]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Scan SBOM for vulnerabilities
        uses: anchore/scan-action@v3
        with:
          sbom: sbom.spdx.json
          fail-build: false

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

**After (Reusable Workflow):**

```yaml
name: Generate SBOM

on:
  push:
    branches: [main]

jobs:
  sbom:
    uses: samuelho-dev/git-flow/.github/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      format: spdx-json
      scan-sbom: true
```

**Savings:** 28 lines → 11 lines (61% reduction)

---

## Kubernetes/Helm Workflows

### Migrate: Helm Chart Linting

**Before (Inline Commands):**

```yaml
name: Helm Lint

on:
  push:
    paths:
      - 'charts/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Helm
        uses: azure/setup-helm@v4
        with:
          version: 'v3.16.3'

      - name: Lint Helm chart
        run: helm lint charts/my-app

      - name: Install kubeconform
        run: |
          wget https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz
          tar xf kubeconform-linux-amd64.tar.gz
          sudo mv kubeconform /usr/local/bin

      - name: Template and validate
        run: |
          helm template charts/my-app | kubeconform -strict
```

**After (Reusable Workflow):**

```yaml
name: Helm Lint

on:
  push:
    paths:
      - 'charts/**'

jobs:
  lint:
    uses: samuelho-dev/git-flow/.github/workflows/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
```

**Savings:** 30 lines → 8 lines (73% reduction)

---

### Migrate: Helm Chart Publishing

**Before (Inline Commands):**

```yaml
name: Publish Helm Chart

on:
  push:
    branches: [main]
    paths:
      - 'charts/**'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Log in to GHCR
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | helm registry login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Package chart
        run: |
          helm package charts/my-app

      - name: Push chart
        run: |
          helm push my-app-*.tgz oci://ghcr.io/${{ github.repository_owner }}/charts
```

**After (Reusable Workflow):**

```yaml
name: Publish Helm Chart

on:
  push:
    branches: [main]
    paths:
      - 'charts/**'

jobs:
  publish:
    uses: samuelho-dev/git-flow/.github/helm-publish.yml@v1
    with:
      chart-path: charts/my-app
      registry: ghcr.io
    secrets: inherit
```

**Savings:** 30 lines → 12 lines (60% reduction)

---

## Terraform Workflows

### Migrate: Terraform Validation

**Before (Inline Commands):**

```yaml
name: Terraform Validate

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Format Check
        run: terraform fmt -check -recursive
        working-directory: terraform/

      - name: Terraform Validate
        run: terraform validate
        working-directory: terraform/

      - name: Run tfsec
        uses: aquasecurity/tfsec-action@v1.0.3
        with:
          working_directory: terraform/
```

**After (Reusable Workflow):**

```yaml
name: Terraform Validate

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  validate:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-validate.yml@v1
    with:
      terraform-path: terraform/
      format-check: true
      security-scan: true
```

**Savings:** 32 lines → 10 lines (69% reduction)

---

### Migrate: Terraform Plan

**Before (Inline Commands):**

```yaml
name: Terraform Plan

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-west-2

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Plan
        run: terraform plan -out=tfplan
        working-directory: terraform/

      - name: Save plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: terraform/tfplan
```

**After (Reusable Workflow):**

```yaml
name: Terraform Plan

on:
  pull_request:
    paths:
      - 'terraform/**'

permissions:
  id-token: write
  pull-requests: write

jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/
      post-pr-comment: true
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

**Savings:** 40 lines → 14 lines (65% reduction)

**Added Benefits:**
- 💬 Automated PR comments with plan summary
- 📊 Has-changes output to gate apply jobs

---

### Migrate: Terraform Apply

**Before (Inline Commands):**

```yaml
name: Terraform Apply

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-west-2

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: terraform/
```

**After (Reusable Workflow):**

```yaml
name: Terraform Apply

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

permissions:
  id-token: write

jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}

  apply:
    needs: plan
    uses: samuelho-dev/git-flow/.github/workflows/terraform-apply.yml@v1
    with:
      terraform-path: terraform/
      plan-artifact-name: ${{ needs.plan.outputs.plan-artifact-name }}
      environment: production
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

**Savings:** 35 lines → 20 lines (43% reduction)

**Added Benefits:**
- ✅ Required-reviewer approval gate via GitHub Environment
- 🔒 OIDC — no static AWS credentials
- 📦 Plan artifact ensures apply matches reviewed plan

---

## Common Migration Patterns

### Pattern 1: Parallel Testing

Run old and new workflows side-by-side during migration:

```yaml
name: Migration Testing

on:
  push:
    branches: [main]

jobs:
  # Old workflow (to be deprecated)
  build-old:
    name: Build (Old - Deprecated)
    runs-on: ubuntu-latest
    steps:
      # ... existing inline steps ...

  # New reusable workflow
  build-new:
    name: Build (New - Testing)
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
      push: true
    secrets: inherit

  # Comparison step
  compare:
    name: Compare Results
    needs: [build-old, build-new]
    runs-on: ubuntu-latest
    steps:
      - name: Compare outputs
        run: |
          echo "Both workflows completed successfully"
          echo "Old: ${{ needs.build-old.result }}"
          echo "New: ${{ needs.build-new.result }}"
```

### Pattern 2: Feature Flag Migration

Use workflow_dispatch to test new workflow before enabling on push:

```yaml
name: Feature Flag Migration

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      use-reusable-workflow:
        description: 'Use new reusable workflow'
        type: boolean
        default: false

jobs:
  build-inline:
    name: Build (Inline)
    if: github.event_name == 'push' || !inputs.use-reusable-workflow
    runs-on: ubuntu-latest
    steps:
      # ... inline steps ...

  build-reusable:
    name: Build (Reusable)
    if: github.event_name == 'workflow_dispatch' && inputs.use-reusable-workflow
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
    secrets: inherit
```

### Pattern 3: Gradual Rollout

Migrate one job at a time:

```yaml
name: Gradual Migration

on:
  push:
    branches: [main]

jobs:
  # ✅ Migrated: Using reusable workflow
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
    secrets: inherit

  # ⏳ Not migrated yet: Still using inline steps
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      # ... inline deployment steps ...

  # ⏳ Not migrated yet: Still using inline steps
  notify:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      # ... inline notification steps ...
```

---

## Troubleshooting

### Issue: "Repository not found" or "Workflow not found"

**Symptom:**
```
Error: samuelho-dev/git-flow/.github/docker-build-push.yml@v1 not found
```

**Solution:**
1. Verify repository name is correct
2. Ensure workflow file exists at specified path
3. Check you're using correct version tag (`@v1` vs `@main`)
4. Verify repository is public or you have access

---

### Issue: Secrets not being passed

**Symptom:**
```
Error: Input required and not supplied: registry-password
```

**Solution:**

Use `secrets: inherit` to pass all secrets:

```yaml
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
    secrets: inherit  # ← Add this
```

Or pass secrets explicitly:

```yaml
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app
    secrets:
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

---

### Issue: Permissions errors

**Symptom:**
```
Error: Resource not accessible by integration
```

**Solution:**

Add required permissions to calling workflow:

```yaml
name: Build

on:
  push:

permissions:
  contents: read
  packages: write      # ← For GHCR push
  security-events: write  # ← For SARIF uploads
  id-token: write      # ← For OIDC/Cosign

jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    # ...
```

---

### Issue: Context not available in reusable workflow

**Symptom:**
```
Error: ${{ github.repository }} not available in this context
```

**Solution:**

Pass GitHub context as inputs:

```yaml
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: ${{ github.event.repository.name }}  # ← Evaluate in caller
      push: ${{ github.ref == 'refs/heads/main' }}  # ← Conditional logic
```

---

### Issue: Artifact not found between jobs

**Symptom:**
```
Error: Unable to find artifact for name: terraform-plan-abc123
```

**Solution:**

Ensure artifact names match exactly:

```yaml
jobs:
  plan:
    uses: samuelho-dev/git-flow/.github/workflows/terraform-plan.yml@v1
    with:
      terraform-path: terraform/
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}

  apply:
    needs: plan
    uses: samuelho-dev/git-flow/.github/workflows/terraform-apply.yml@v1
    with:
      terraform-path: terraform/
      plan-artifact-name: ${{ needs.plan.outputs.plan-artifact-name }}  # ← Use the output directly
    secrets:
      aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
```

---

### Issue: Workflow runs but doesn't appear to do anything

**Symptom:**
Workflow completes successfully but expected outputs are missing.

**Solution:**

Check input parameters are being passed correctly:

```yaml
# ❌ Wrong: Missing required inputs
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    secrets: inherit

# ✅ Correct: All required inputs provided
jobs:
  build:
    uses: samuelho-dev/git-flow/.github/docker-build-push.yml@v1
    with:
      image: my-app  # ← Required input
      push: true
    secrets: inherit
```

---

## Migration Checklist

Use this checklist to track your migration progress:

### Pre-Migration

- [ ] Audit existing workflows
- [ ] Identify migration candidates
- [ ] Review [USAGE.md](USAGE.md) documentation
- [ ] Review [EXAMPLES.md](EXAMPLES.md) for patterns
- [ ] Set up test repository for validation

### During Migration

- [ ] Create migration branch
- [ ] Update workflow file
- [ ] Test with workflow_dispatch
- [ ] Compare old vs new outputs
- [ ] Update documentation/README
- [ ] Create PR with migration

### Post-Migration

- [ ] Monitor first 3-5 runs
- [ ] Verify expected outputs
- [ ] Check artifact retention
- [ ] Update team documentation
- [ ] Remove old workflow (after 2 weeks)

### Rollback Plan

- [ ] Keep old workflow committed but disabled
- [ ] Document rollback procedure
- [ ] Test rollback process
- [ ] Set calendar reminder to clean up old workflow

---

## Need Help?

- **Documentation**: [USAGE.md](USAGE.md) | [EXAMPLES.md](EXAMPLES.md)
- **Issues**: [GitHub Issues](https://github.com/samuelho-dev/git-flow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/samuelho-dev/git-flow/discussions)

---

**Migration Support**

If you encounter issues during migration:
1. Check [Troubleshooting](#troubleshooting) section
2. Search [existing issues](https://github.com/samuelho-dev/git-flow/issues)
3. Create new issue with `migration` label

**Last Updated:** 2025-01-20
