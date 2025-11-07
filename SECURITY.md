# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

Use GitHub's **Private Vulnerability Reporting** feature:

1. Go to the [Security tab](https://github.com/simplemindedbot/cortexgraph/security)
2. Click **"Report a vulnerability"**
3. Fill out the advisory form with details
4. Submit privately to the maintainers

This keeps the vulnerability confidential until a fix is released.

### What to Include

Please include:
- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Impact** assessment (what can an attacker do?)
- **Suggested fix** (if you have one)
- **Affected versions**

## Response Timeline

- **Initial Response**: Within 72 hours
- **Status Update**: Within 1 week
- **Fix Timeline**: Depends on severity
  - **Critical**: 1-7 days
  - **High**: 1-4 weeks
  - **Medium**: 1-2 months
  - **Low**: Best effort

## Disclosure Policy

- Security issues will be disclosed **after a fix is released**
- We follow coordinated disclosure practices
- We'll credit reporters in the release notes (unless you prefer to remain anonymous)

## Security Best Practices

For users of CortexGraph:

### File Permissions
- Configuration files are created with `0600` (user read/write only)
- Storage directory should be `0700` (user access only)

### Sensitive Data
- Never commit `.env` files to git
- Use `.gitignore` to exclude sensitive files
- Review logs before sharing for debugging

### Supply Chain
- Verify package signatures when installing
- Pin dependencies in production
- Monitor Dependabot alerts

## Security Features

CortexGraph includes:
- ✅ Input validation on all MCP tools
- ✅ Path traversal prevention
- ✅ No network communication (fully local)
- ✅ No telemetry or analytics
- 🚧 Dependency scanning (planned v1.1.0)
- ✅ SBOM generation (CycloneDX) in CI

## SBOM (Software Bill of Materials)

This repository automatically generates a CycloneDX SBOM in CI for each push/PR via the security workflow. You can find the generated `sbom.json` as an artifact in the “Security Scanning” workflow run.

For more about CycloneDX: https://cyclonedx.org/

## Known Limitations

- No encryption at rest (files stored as plaintext JSONL/Markdown)
- No multi-user isolation (single-user system)
- File locking uses OS-level mechanisms (not cluster-safe)

If you need encryption, consider using:
- Full disk encryption (FileVault, BitLocker, LUKS)
- Encrypted home directories
- Encrypted git repositories

## Updates and Patches

Security patches are released as:
- Patch versions for v1.0.x (e.g., 1.0.1, 1.0.2)
- Announced via GitHub Releases
- Documented in CHANGELOG.md

Subscribe to releases: https://github.com/simplemindedbot/cortexgraph/releases

## Contact

- **Security issues**: Use GitHub's private vulnerability reporting (see above)
- **General issues**: https://github.com/simplemindedbot/cortexgraph/issues
