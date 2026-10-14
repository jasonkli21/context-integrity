# Security

Context Integrity processes repository content, which should be treated as untrusted input.

During early development:

- scanning should not execute repository files;
- network access should not be required for core scans;
- symlinks must not escape the repository root;
- inventory output should avoid raw source contents and local absolute paths by default.

If you discover a security issue, do not open a public exploit report containing sensitive details. Use the repository owner's preferred private reporting channel once one is published.
