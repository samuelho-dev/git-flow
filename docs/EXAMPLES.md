# 📝 Workflow Examples

Complete examples for common CI/CD scenarios using git-flow reusable workflows.

## Table of Contents

1. [Complete CI/CD Pipeline](#complete-cicd-pipeline)
2. [Multi-Service Monorepo](#multi-service-monorepo)
3. [Security-First Pipeline](#security-first-pipeline)
4. [Multi-Platform Builds](#multi-platform-builds)
5. [Pull Request Workflows](#pull-request-workflows)
6. [Scheduled Security Scans](#scheduled-security-scans)
7. [Helm Chart CI/CD](#helm-chart-cicd)
8. [Kyverno Policy Testing](#kyverno-policy-testing)
9. [Terraform CI/CD](#terraform-cicd)
10. [GitOps Pipeline](#gitops-pipeline)

---

## Complete CI/CD Pipeline

Full CI/CD pipeline with testing, building, scanning, and deployment.

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:

permissions:
  contents: write
  packages: write
  id-token: write
  security-events: write

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # Stage 1: Security Scans
  scan-secrets:
    name: Scan for Secrets
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true

  scan-vulnerabilities:
    name: Scan for Vulnerabilities
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: HIGH,CRITICAL

  # Stage 2: Build & Test
  build:
    name: Build Docker Image
    needs: [scan-secrets, scan-vulnerabilities]
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./Dockerfile
      image: my-app
      platforms: linux/amd64,linux/arm64
      push: ${{ github.ref == 'refs/heads/main' }}
      scan: true
      sign: true
      sbom: true
    secrets: inherit

  # Stage 3: Generate SBOM
  sbom:
    name: Generate SBOM
    needs: build
    if: github.ref == 'refs/heads/main'
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: image
      target: ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }}
      format: spdx-json
      scan-sbom: true

  # Stage 4: Deploy (example - add your deployment logic)
  deploy:
    name: Deploy to Production
    needs: [build, sbom]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy notification
        run: echo "Deploy to production with tag sha-${{ github.sha }}"
```

---

## Multi-Service Monorepo

Build multiple services in parallel from a monorepo.

```yaml
name: Monorepo CI/CD

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: write
  packages: write
  id-token: write
  security-events: write

jobs:
  # Security scans run once for entire repo
  security:
    name: Security Scans
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .

  secrets:
    name: Secret Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1

  # Build backend service
  build-backend:
    name: Build Backend
    needs: [security, secrets]
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./services/backend/Dockerfile
      image: my-app-backend
      build-args: |
        SERVICE=backend
        NODE_ENV=production
    secrets: inherit

  # Build frontend service
  build-frontend:
    name: Build Frontend
    needs: [security, secrets]
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./services/frontend/Dockerfile
      image: my-app-frontend
      build-args: |
        SERVICE=frontend
        NODE_ENV=production
    secrets: inherit

  # Build worker service
  build-worker:
    name: Build Worker
    needs: [security, secrets]
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./services/worker/Dockerfile
      image: my-app-worker
      build-args: |
        SERVICE=worker
    secrets: inherit

  # Summary job
  summary:
    name: Build Summary
    needs: [build-backend, build-frontend, build-worker]
    runs-on: ubuntu-latest
    steps:
      - name: Generate summary
        run: |
          echo "### ✅ All services built successfully" >> $GITHUB_STEP_SUMMARY
          echo "- Backend: sha-${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "- Frontend: sha-${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "- Worker: sha-${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
```

---

## Security-First Pipeline

Comprehensive security scanning with multiple tools.

```yaml
name: Security Pipeline

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2 AM

permissions:
  contents: read
  security-events: write

jobs:
  # Scan 1: Secrets
  gitleaks:
    name: Secret Detection
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
      format: sarif

  # Scan 2: Filesystem Vulnerabilities
  trivy-fs:
    name: Filesystem Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: HIGH,CRITICAL

  # Scan 3: Configuration Issues
  trivy-config:
    name: Configuration Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: config
      scan-ref: deploy/
      severity: MEDIUM,HIGH,CRITICAL

  # Scan 4: Docker Image
  trivy-image:
    name: Image Scan
    needs: trivy-fs
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: image
      scan-ref: ghcr.io/${{ github.repository_owner }}/my-app:latest
      severity: HIGH,CRITICAL

  # Scan 5: SBOM Analysis
  sbom-scan:
    name: SBOM Vulnerability Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      scan-sbom: true

  # Report Summary
  security-report:
    name: Security Report
    needs: [gitleaks, trivy-fs, trivy-config, trivy-image, sbom-scan]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Generate security report
        run: |
          echo "## 🛡️  Security Scan Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "All security scans completed. Check Security tab for details." >> $GITHUB_STEP_SUMMARY
```

---

## Multi-Platform Builds

Build Docker images for multiple platforms (amd64, arm64, arm/v7).

```yaml
name: Multi-Platform Build

on:
  push:
    tags:
      - 'v*'
  release:
    types: [published]

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  build:
    name: Build Multi-Platform Image
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./Dockerfile
      image: my-app
      platforms: linux/amd64,linux/arm64,linux/arm/v7
      push: true
      scan: true
      sign: true
      sbom: true
      cache-registry: true
      build-args: |
        VERSION=${{ github.ref_name }}
        BUILD_DATE=${{ github.event.repository.updated_at }}
    secrets: inherit

  # Test images on different architectures
  test-amd64:
    name: Test AMD64
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Test AMD64 image
        run: |
          docker pull ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }}
          docker run --rm ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }} --version

  test-arm64:
    name: Test ARM64
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Test ARM64 image
        run: |
          docker pull --platform linux/arm64 ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }}
          docker run --platform linux/arm64 --rm ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }} --version
```

---

## Pull Request Workflows

Optimized workflows for pull request validation.

```yaml
name: Pull Request

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  security-events: write

concurrency:
  group: pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  # Fast security checks
  security:
    name: Security Checks
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true

  # Build without pushing
  build:
    name: Build & Test
    needs: security
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app
      push: false  # Don't push on PR
      scan: true
      sign: false  # Skip signing on PR
      sbom: false  # Skip SBOM on PR
      platforms: linux/amd64  # Single platform for speed
    secrets: inherit

  # Comment on PR
  comment:
    name: PR Comment
    needs: build
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `### ✅ Build Successful\n\nImage: \`ghcr.io/${context.repo.owner}/my-app:sha-${context.sha.substring(0, 7)}\``
            })
```

---

## Scheduled Security Scans

Run security scans on a schedule (e.g., weekly).

```yaml
name: Scheduled Security Scans

on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2 AM
  workflow_dispatch:  # Allow manual trigger

permissions:
  contents: read
  security-events: write
  issues: write  # Create issues for findings

jobs:
  scan-repo:
    name: Repository Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: fs
      scan-ref: .
      severity: MEDIUM,HIGH,CRITICAL

  scan-secrets:
    name: Secret Scan
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: false  # Report only

  scan-images:
    name: Image Scan
    strategy:
      matrix:
        image:
          - my-app-backend
          - my-app-frontend
          - my-app-worker
    uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
    with:
      scan-type: image
      scan-ref: ghcr.io/${{ github.repository_owner }}/${{ matrix.image }}:latest
      severity: HIGH,CRITICAL

  sbom-check:
    name: SBOM Vulnerability Check
    uses: samuelho-dev/git-flow/.github/workflows/security/sbom-generate.yml@v1
    with:
      target-type: directory
      target: .
      scan-sbom: true

  # Create issue if vulnerabilities found
  report:
    name: Create Report
    needs: [scan-repo, scan-secrets, scan-images, sbom-check]
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Create issue
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `🔒 Weekly Security Scan: Vulnerabilities Found`,
              body: `Scheduled security scan on ${new Date().toISOString()} found vulnerabilities.\n\nCheck the [Security tab](https://github.com/${context.repo.owner}/${context.repo.repo}/security) for details.`,
              labels: ['security', 'automated']
            })
```

---

## Advanced: Custom Workflow with Composite Actions

Use composite actions for custom workflows.

```yaml
name: Custom Build

on:
  push:
    branches: [main]

jobs:
  custom-build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      # Use composite action for setup
      - name: Setup Node.js with pnpm
        uses: samuelho-dev/git-flow/actions/setup-node-pnpm@v1
        with:
          node-version: 20
          pnpm-version: 8

      # Build application
      - name: Build
        run: pnpm build

      # Use composite action for Kubernetes tools
      - name: Setup Kubernetes tools
        uses: samuelho-dev/git-flow/actions/setup-kubernetes-tools@v1
        with:
          install-helm: true
          install-kubectl: true

      # Custom Docker build steps
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/my-app:${{ github.sha }}

      # Use reusable workflow for security scan
      - name: Scan image
        uses: samuelho-dev/git-flow/.github/workflows/security/trivy-scan.yml@v1
        with:
          scan-type: image
          scan-ref: ghcr.io/${{ github.repository_owner }}/my-app:${{ github.sha }}
```

---

## Helm Chart CI/CD

Complete CI/CD pipeline for Helm charts with lint, test, and publish.

```yaml
name: Helm Chart CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'charts/**'
  pull_request:
    paths:
      - 'charts/**'

permissions:
  contents: write
  packages: write
  id-token: write
  checks: write

jobs:
  # Stage 1: Lint
  lint:
    name: Lint Helm Chart
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-lint.yml@v1
    with:
      chart-path: charts/my-app
      strict: true
      kubeconform: true
      kubernetes-version: '1.30.0'
      helm-docs-check: true
      schema-validation: true

  # Stage 2: Test
  test:
    name: Test Helm Chart
    needs: lint
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-test.yml@v1
    with:
      chart-path: charts/my-app
      output-format: junit
      fail-fast: false

  # Stage 3: Publish (only on main branch)
  publish:
    name: Publish Helm Chart
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-publish.yml@v1
    with:
      chart-path: charts/my-app
      registry: ghcr.io
      sign-chart: true
      create-release: true
      provenance: true
    secrets: inherit

  # Stage 4: Verify Published Chart
  verify:
    name: Verify Published Chart
    needs: publish
    runs-on: ubuntu-latest
    steps:
      - name: Setup Helm
        uses: samuelho-dev/git-flow/actions/setup-kubernetes-tools@v1
        with:
          install-helm: true
          install-cosign: true

      - name: Login to GHCR
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | helm registry login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Pull and verify chart
        run: |
          CHART_VERSION=$(helm show chart oci://ghcr.io/${{ github.repository_owner }}/charts/my-app | grep '^version:' | awk '{print $2}')
          helm pull oci://ghcr.io/${{ github.repository_owner }}/charts/my-app --version $CHART_VERSION
          cosign verify oci://ghcr.io/${{ github.repository_owner }}/charts/my-app:$CHART_VERSION
```

### Multi-Chart Repository

Lint and test multiple charts in parallel.

```yaml
name: Multi-Chart CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  # Find all charts
  find-charts:
    runs-on: ubuntu-latest
    outputs:
      charts: ${{ steps.find.outputs.charts }}
    steps:
      - uses: actions/checkout@v4
      - id: find
        run: |
          CHARTS=$(find charts -maxdepth 1 -mindepth 1 -type d -exec basename {} \; | jq -R -s -c 'split("\n")[:-1]')
          echo "charts=$CHARTS" >> $GITHUB_OUTPUT

  # Lint all charts
  lint:
    name: Lint ${{ matrix.chart }}
    needs: find-charts
    strategy:
      matrix:
        chart: ${{ fromJson(needs.find-charts.outputs.charts) }}
      fail-fast: false
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-lint.yml@v1
    with:
      chart-path: charts/${{ matrix.chart }}

  # Test all charts
  test:
    name: Test ${{ matrix.chart }}
    needs: [find-charts, lint]
    strategy:
      matrix:
        chart: ${{ fromJson(needs.find-charts.outputs.charts) }}
      fail-fast: false
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-test.yml@v1
    with:
      chart-path: charts/${{ matrix.chart }}

  # Publish all charts (main branch only)
  publish:
    name: Publish ${{ matrix.chart }}
    needs: [find-charts, test]
    if: github.ref == 'refs/heads/main'
    strategy:
      matrix:
        chart: ${{ fromJson(needs.find-charts.outputs.charts) }}
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/helm-publish.yml@v1
    with:
      chart-path: charts/${{ matrix.chart }}
    secrets: inherit
```

---

## Kyverno Policy Testing

Test Kyverno policies with comprehensive validation.

```yaml
name: Kyverno Policy CI

on:
  push:
    branches: [main]
    paths:
      - 'policies/**'
  pull_request:
    paths:
      - 'policies/**'

permissions:
  contents: read
  checks: write

jobs:
  # Validate and test policies
  test-policies:
    name: Test Kyverno Policies
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/kyverno-test.yml@v1
    with:
      policy-path: policies/
      test-path: tests/chainsaw
      test-framework: both
      kyverno-version: v1.13.0
      chainsaw-version: v0.2.14
      validate-policies: true
      report-format: junit

  # Deploy policies to cluster (main branch only)
  deploy:
    name: Deploy Policies
    needs: test-policies
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup kubectl
        uses: samuelho-dev/git-flow/actions/setup-kubernetes-tools@v1
        with:
          install-kubectl: true

      - name: Deploy to cluster
        run: |
          # Configure kubectl (add your cluster config here)
          kubectl apply -f policies/ --dry-run=server
          kubectl apply -f policies/
```

### Multi-Environment Policy Testing

Test policies across different Kubernetes versions.

```yaml
name: Kyverno Multi-Environment Test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test-k8s-versions:
    name: Test on k8s ${{ matrix.k8s-version }}
    strategy:
      matrix:
        k8s-version: ['1.28.0', '1.29.0', '1.30.0']
      fail-fast: false
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Kyverno CLI
        run: |
          KYVERNO_VERSION="v1.13.0"
          wget -q "https://github.com/kyverno/kyverno/releases/download/${KYVERNO_VERSION}/kyverno-cli_${KYVERNO_VERSION}_linux_x86_64.tar.gz"
          tar -xzf "kyverno-cli_${KYVERNO_VERSION}_linux_x86_64.tar.gz"
          sudo mv kyverno /usr/local/bin/

      - name: Test policies
        run: |
          cd policies/
          kyverno test . --detailed-results

  # Run full test suite with Chainsaw
  test-chainsaw:
    name: Chainsaw Integration Tests
    uses: samuelho-dev/git-flow/.github/workflows/kubernetes/kyverno-test.yml@v1
    with:
      policy-path: policies/
      test-framework: chainsaw
      fail-fast: true
```

---

## Terraform CI/CD

Complete Infrastructure as Code pipeline with validation, planning, and deployment.

### Complete Terraform Pipeline

Full Terraform workflow with validate → plan → apply stages.

```yaml
name: Terraform CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'
  pull_request:
    paths:
      - 'terraform/**'

permissions:
  contents: read
  pull-requests: write
  id-token: write
  security-events: write

jobs:
  # Stage 1: Validate
  validate:
    name: Validate Terraform
    uses: samuelho-dev/git-flow/.github/workflows/terraform/validate.yml@v1
    with:
      terraform-path: terraform/environments/prod
      terraform-version: 1.9.8
      fmt-check: true
      tfsec-scan: true
      checkov-scan: true
      terraform-docs-check: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}

  # Stage 2: Plan (on all branches)
  plan:
    name: Plan Infrastructure Changes
    needs: validate
    uses: samuelho-dev/git-flow/.github/workflows/terraform/plan.yml@v1
    with:
      terraform-path: terraform/environments/prod
      terraform-version: 1.9.8
      upload-plan: true
      enable-infracost: true
      post-pr-comment: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}

  # Stage 3: Apply (main branch only)
  apply:
    name: Apply Infrastructure Changes
    needs: plan
    if: github.ref == 'refs/heads/main'
    uses: samuelho-dev/git-flow/.github/workflows/terraform/apply.yml@v1
    with:
      terraform-path: terraform/environments/prod
      terraform-version: 1.9.8
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: production  # Requires approval
      backup-state: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  # Stage 4: Verification
  verify:
    name: Post-Apply Verification
    needs: apply
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Verify infrastructure
        run: |
          echo "✅ Infrastructure deployed successfully"
          echo "Revision: ${{ github.sha }}"
          echo "Environment: production"
```

### Multi-Environment Terraform

Deploy infrastructure to multiple environments with matrix strategy.

```yaml
name: Multi-Environment Infrastructure

on:
  push:
    branches: [main, develop]
    paths:
      - 'terraform/**'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - dev
          - staging
          - production

permissions:
  contents: read
  id-token: write
  security-events: write

jobs:
  # Determine which environments to deploy
  select-environment:
    runs-on: ubuntu-latest
    outputs:
      environments: ${{ steps.set-env.outputs.environments }}
    steps:
      - id: set-env
        run: |
          if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            # Manual trigger: deploy to selected environment
            echo "environments=[\"${{ inputs.environment }}\"]" >> $GITHUB_OUTPUT
          elif [ "${{ github.ref }}" == "refs/heads/main" ]; then
            # Main branch: deploy to staging and production
            echo "environments=[\"staging\", \"production\"]" >> $GITHUB_OUTPUT
          else
            # Develop branch: deploy to dev
            echo "environments=[\"dev\"]" >> $GITHUB_OUTPUT
          fi

  # Validate all environments
  validate:
    name: Validate ${{ matrix.env }}
    strategy:
      matrix:
        env: [dev, staging, production]
      fail-fast: false
    uses: samuelho-dev/git-flow/.github/workflows/terraform/validate.yml@v1
    with:
      terraform-path: terraform/environments/${{ matrix.env }}
      tfsec-scan: true
      checkov-scan: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}

  # Plan for selected environments
  plan:
    name: Plan ${{ matrix.env }}
    needs: [select-environment, validate]
    strategy:
      matrix:
        env: ${{ fromJson(needs.select-environment.outputs.environments) }}
    uses: samuelho-dev/git-flow/.github/workflows/terraform/plan.yml@v1
    with:
      terraform-path: terraform/environments/${{ matrix.env }}
      upload-plan: true
      enable-infracost: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}

  # Apply to selected environments sequentially
  apply-dev:
    name: Apply to Dev
    needs: plan
    if: contains(fromJson(needs.select-environment.outputs.environments), 'dev')
    uses: samuelho-dev/git-flow/.github/workflows/terraform/apply.yml@v1
    with:
      terraform-path: terraform/environments/dev
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: development
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  apply-staging:
    name: Apply to Staging
    needs: [plan, apply-dev]
    if: |
      always() &&
      !cancelled() &&
      (needs.apply-dev.result == 'success' || needs.apply-dev.result == 'skipped') &&
      contains(fromJson(needs.select-environment.outputs.environments), 'staging')
    uses: samuelho-dev/git-flow/.github/workflows/terraform/apply.yml@v1
    with:
      terraform-path: terraform/environments/staging
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: staging
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  apply-production:
    name: Apply to Production
    needs: [plan, apply-staging]
    if: |
      always() &&
      !cancelled() &&
      (needs.apply-staging.result == 'success' || needs.apply-staging.result == 'skipped') &&
      contains(fromJson(needs.select-environment.outputs.environments), 'production')
    uses: samuelho-dev/git-flow/.github/workflows/terraform/apply.yml@v1
    with:
      terraform-path: terraform/environments/production
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: production  # Requires manual approval
      backup-state: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Terraform with Security Focus

Infrastructure pipeline with comprehensive security scanning.

```yaml
name: Secure Infrastructure Pipeline

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 3 * * 1'  # Weekly Monday 3 AM

permissions:
  contents: read
  pull-requests: write
  security-events: write
  id-token: write

jobs:
  # Security validation
  validate:
    name: Security Validation
    uses: samuelho-dev/git-flow/.github/workflows/terraform/validate.yml@v1
    with:
      terraform-path: terraform/
      terraform-version: 1.9.8
      fmt-check: true
      tfsec-scan: true
      tfsec-severity: MEDIUM,HIGH,CRITICAL
      checkov-scan: true
      checkov-severity: MEDIUM,HIGH,CRITICAL
      terraform-docs-check: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}

  # Additional secret scanning
  scan-secrets:
    name: Scan for Secrets
    uses: samuelho-dev/git-flow/.github/workflows/security/gitleaks-scan.yml@v1
    with:
      fail-on-findings: true
      format: sarif

  # Cost estimation
  plan-with-cost:
    name: Plan with Cost Estimation
    needs: [validate, scan-secrets]
    uses: samuelho-dev/git-flow/.github/workflows/terraform/plan.yml@v1
    with:
      terraform-path: terraform/
      enable-infracost: true
      post-pr-comment: true
      upload-plan: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}

  # Apply with approval gate
  apply:
    name: Apply Infrastructure
    needs: plan-with-cost
    if: github.ref == 'refs/heads/main'
    uses: samuelho-dev/git-flow/.github/workflows/terraform/apply.yml@v1
    with:
      terraform-path: terraform/
      plan-artifact-name: terraform-plan-${{ github.sha }}
      environment: production
      backup-state: true
    secrets:
      terraform-token: ${{ secrets.TF_API_TOKEN }}
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  # Security report
  security-report:
    name: Security Report
    needs: [validate, scan-secrets, plan-with-cost]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Generate security summary
        run: |
          echo "## 🔒 Infrastructure Security Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- tfsec scan: ${{ needs.validate.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Checkov scan: ${{ needs.validate.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Secret scan: ${{ needs.scan-secrets.result }}" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Check Security tab for detailed findings." >> $GITHUB_STEP_SUMMARY
```

---

## GitOps Pipeline

Complete CI → GitOps → CD pipelines with automated manifest updates and ArgoCD sync.

### Complete GitOps Pipeline

End-to-end pipeline: Build Docker image → Update manifests → Sync ArgoCD.

```yaml
name: GitOps CI/CD Pipeline

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'

permissions:
  contents: write
  packages: write
  id-token: write
  security-events: write

jobs:
  # Stage 1: Build and push Docker image
  build:
    name: Build & Push Image
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      context: .
      dockerfile: ./Dockerfile
      image: my-app
      platforms: linux/amd64,linux/arm64
      push: true
      scan: true
      sign: true
      sbom: true
    secrets: inherit

  # Stage 2: Update Kubernetes manifests
  update-manifests:
    name: Update Manifests
    needs: build
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/k8s/overlays/production
      update-type: image
      image-name: ghcr.io/${{ github.repository_owner }}/my-app
      image-tag: sha-${{ github.sha }}
      file-pattern: '**/*.yaml'
      commit-message: |
        chore(gitops): update my-app to sha-${{ github.sha }}

        - Source commit: ${{ github.sha }}
        - Triggered by: @${{ github.actor }}
        - Workflow: ${{ github.workflow }}
      create-pr: false  # Direct commit to main
      target-branch: main

  # Stage 3: Sync ArgoCD application
  argocd-sync:
    name: Sync ArgoCD
    needs: update-manifests
    uses: samuelho-dev/git-flow/.github/workflows/gitops/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app-production
      sync-strategy: auto
      prune: false
      force: false
      wait-for-sync: true
      sync-timeout: 300
      health-check: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}

  # Stage 4: Verification
  verify-deployment:
    name: Verify Deployment
    needs: argocd-sync
    runs-on: ubuntu-latest
    steps:
      - name: Verify deployment
        run: |
          echo "## ✅ Deployment Successful" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Application:** my-app-production" >> $GITHUB_STEP_SUMMARY
          echo "**Image:** ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "**Sync Status:** ${{ needs.argocd-sync.outputs.sync-status }}" >> $GITHUB_STEP_SUMMARY
          echo "**Health Status:** ${{ needs.argocd-sync.outputs.health-status }}" >> $GITHUB_STEP_SUMMARY

      - name: Send notification
        run: |
          # Add your notification logic here (Slack, email, etc.)
          echo "Deployment notification sent"
```

### GitOps with Pull Request

Create PR for manifest updates instead of direct commit (safer for production).

```yaml
name: GitOps with PR

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'

permissions:
  contents: write
  packages: write
  pull-requests: write
  id-token: write

jobs:
  # Build image
  build:
    name: Build Image
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app
      push: true
      scan: true
    secrets: inherit

  # Create PR with manifest updates
  update-manifests:
    name: Update Manifests via PR
    needs: build
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/k8s/production
      update-type: image
      image-name: ghcr.io/${{ github.repository_owner }}/my-app
      image-tag: sha-${{ github.sha }}
      commit-message: |
        chore(gitops): update my-app to sha-${{ github.sha }}
      create-pr: true  # Create PR instead of direct commit
      pr-branch: gitops/my-app-sha-${{ github.sha }}
      target-branch: main

  # Comment on PR with deployment info
  pr-comment:
    name: Add Deployment Info to PR
    needs: update-manifests
    if: needs.update-manifests.outputs.pr-url != ''
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            const prUrl = '${{ needs.update-manifests.outputs.pr-url }}';
            const prNumber = prUrl.split('/').pop();

            github.rest.issues.createComment({
              issue_number: prNumber,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🚀 Deployment Ready

              **Image:** \`ghcr.io/${{ github.repository_owner }}/my-app:sha-${{ github.sha }}\`
              **Files Updated:** ${{ needs.update-manifests.outputs.files-updated }}

              ### Next Steps
              1. Review manifest changes
              2. Merge this PR to trigger ArgoCD sync
              3. Monitor application health in ArgoCD dashboard

              ---
              *Triggered by: ${{ github.sha }} (@${{ github.actor }})*`
            });
```

### Multi-Application GitOps

Update and sync multiple applications in parallel.

```yaml
name: Multi-Application GitOps

on:
  push:
    branches: [main]

permissions:
  contents: write
  packages: write
  id-token: write

jobs:
  # Build all services
  build-backend:
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app-backend
      dockerfile: ./services/backend/Dockerfile
      push: true
    secrets: inherit

  build-frontend:
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app-frontend
      dockerfile: ./services/frontend/Dockerfile
      push: true
    secrets: inherit

  build-worker:
    uses: samuelho-dev/git-flow/.github/workflows/docker/build-push.yml@v1
    with:
      image: my-app-worker
      dockerfile: ./services/worker/Dockerfile
      push: true
    secrets: inherit

  # Update manifests for all services
  update-backend:
    needs: build-backend
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/k8s/backend
      update-type: image
      image-name: ghcr.io/${{ github.repository_owner }}/my-app-backend
      image-tag: sha-${{ github.sha }}

  update-frontend:
    needs: build-frontend
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/k8s/frontend
      update-type: image
      image-name: ghcr.io/${{ github.repository_owner }}/my-app-frontend
      image-tag: sha-${{ github.sha }}

  update-worker:
    needs: build-worker
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/k8s/worker
      update-type: image
      image-name: ghcr.io/${{ github.repository_owner }}/my-app-worker
      image-tag: sha-${{ github.sha }}

  # Sync all ArgoCD applications
  sync-backend:
    needs: update-backend
    uses: samuelho-dev/git-flow/.github/workflows/gitops/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app-backend
      wait-for-sync: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}

  sync-frontend:
    needs: update-frontend
    uses: samuelho-dev/git-flow/.github/workflows/gitops/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app-frontend
      wait-for-sync: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}

  sync-worker:
    needs: update-worker
    uses: samuelho-dev/git-flow/.github/workflows/gitops/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app-worker
      wait-for-sync: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}

  # Summary
  deployment-summary:
    name: Deployment Summary
    needs: [sync-backend, sync-frontend, sync-worker]
    runs-on: ubuntu-latest
    steps:
      - name: Generate summary
        run: |
          echo "## 🚀 Multi-Application Deployment Complete" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Applications Synced" >> $GITHUB_STEP_SUMMARY
          echo "- **Backend:** ${{ needs.sync-backend.outputs.sync-status }} / ${{ needs.sync-backend.outputs.health-status }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Frontend:** ${{ needs.sync-frontend.outputs.sync-status }} / ${{ needs.sync-frontend.outputs.health-status }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Worker:** ${{ needs.sync-worker.outputs.sync-status }} / ${{ needs.sync-worker.outputs.health-status }}" >> $GITHUB_STEP_SUMMARY
```

### Helm Values Update

Update Helm values files in GitOps repository.

```yaml
name: Update Helm Values

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to update'
        required: true
        type: choice
        options:
          - dev
          - staging
          - production
      helm-key:
        description: 'Helm value key (e.g., image.tag)'
        required: true
        type: string
      helm-value:
        description: 'New value'
        required: true
        type: string

permissions:
  contents: write
  pull-requests: write

jobs:
  update-helm-values:
    name: Update Helm Values
    uses: samuelho-dev/git-flow/.github/workflows/gitops/update-manifests.yml@v1
    with:
      manifest-path: deploy/helm/my-app/environments/${{ inputs.environment }}
      update-type: helm-values
      helm-key: ${{ inputs.helm-key }}
      helm-value: ${{ inputs.helm-value }}
      commit-message: |
        chore(helm): update ${{ inputs.helm-key }} in ${{ inputs.environment }}

        New value: ${{ inputs.helm-value }}
        Triggered by: @${{ github.actor }}
      create-pr: true
      pr-branch: helm/update-${{ inputs.environment }}-${{ github.run_number }}

  sync-after-merge:
    name: Sync ArgoCD (after PR merge)
    needs: update-helm-values
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    uses: samuelho-dev/git-flow/.github/workflows/gitops/argocd-sync.yml@v1
    with:
      argocd-server: argocd.example.com
      argocd-app-name: my-app-${{ inputs.environment }}
      wait-for-sync: true
      health-check: true
    secrets:
      argocd-token: ${{ secrets.ARGOCD_TOKEN }}
```

---

## Need More Examples?

Check out:
- **[Usage Guide](USAGE.md)** - Detailed parameter documentation
- **[Main README](../README.md)** - Quick start examples
- **[GitHub Issues](https://github.com/samuelho-dev/git-flow/issues)** - Ask questions
