# Security

## Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Use GitHub's **Private Vulnerability Reporting** feature:

1. Go to the [Security tab](https://github.com/prefrontal-systems/cortexgraph/security)
2. Click **"Report a vulnerability"**
3. Fill out the advisory form with details

Expected response time: **48 hours**

## Security Measures

### Automated Scanning

CortexGraph uses multiple security scanning tools:

- **Dependabot**: Automated dependency updates
- **pip-audit**: Official PyPA vulnerability scanner
- **Bandit**: Python security linter
- **CodeQL**: Semantic code analysis

Scans run:
- On every push/PR
- Weekly scheduled scans (Mondays 10:00 UTC)
- Manual workflow dispatch

### Supply Chain Security

- Dependencies tracked with Dependabot
- Auto-merge for safe updates (patch/minor dev dependencies)
- All dependencies from trusted sources (PyPI)

### Local-First Privacy

🔒 **All data stored locally** - no cloud services, no tracking, no data sharing.

- Short-term memory: `~/.config/cortexgraph/jsonl/` (JSONL format)
- Long-term memory: Your Obsidian vault (Markdown)
- Configuration: `~/.config/cortexgraph/.env`

### File Permissions

Sensitive files use restrictive permissions:

```python
# Config files: rw------- (0o600)
os.chmod(config_file, 0o600)

# Storage directories: rwx------ (0o700)
os.chmod(storage_dir, 0o700)
```

### Input Validation

All user inputs validated:

- Memory IDs checked for format
- File paths validated (no traversal)
- Tags/entities sanitized
- Content size limits enforced

## Best Practices

### Configuration Security

1. **Never commit `.env` files** to version control
2. **Use restrictive permissions** on config files
3. **Review configuration** before sharing

### Storage Security

1. **Regular backups** - Git integration available
2. **Encrypt disk** for additional protection
3. **Review stored data** periodically

### Integration Security

1. **MCP server** runs locally (no network access)
2. **Claude Desktop** controls access to tools
3. **No external API calls** without explicit config

## Security Roadmap

Ongoing improvements tracked in [Issue #6](https://github.com/prefrontal-systems/cortexgraph/issues/6):

- [ ] SBOM (Software Bill of Materials) generation
- [ ] Dependency pinning with hashes
- [ ] Runtime security audits
- [ ] Additional input validation
- [ ] Path traversal prevention hardening

## Disclosure Policy

When you report a vulnerability:

1. **Acknowledgment**: Within 48 hours
2. **Assessment**: Within 7 days
3. **Fix timeline**: Depends on severity
   - Critical: 24-48 hours
   - High: 7 days
   - Medium: 30 days
   - Low: Next release
4. **Coordinated disclosure**: Work with reporter on timing

## Security Contact

Use GitHub's private reporting feature (link above).

## Security Updates

Subscribe to:
- [GitHub Security Advisories](https://github.com/prefrontal-systems/cortexgraph/security/advisories)
- [Release notifications](https://github.com/prefrontal-systems/cortexgraph/releases)

## License

Security practices follow OWASP guidelines and OSSF best practices.

See also:
- [SECURITY.md](https://github.com/prefrontal-systems/cortexgraph/blob/main/SECURITY.md) (main policy)
- [Contributing guidelines](CONTRIBUTING.md)
