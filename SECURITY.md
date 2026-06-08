# Security and Privacy

image-inpaint works with local documents and local images. Treat those inputs as
potentially sensitive.

## Do Not Commit Sensitive Data

Before publishing or sharing a branch, check for:

- real user documents
- processed outputs
- downloaded remote images
- screenshots from private systems
- API keys or access tokens
- model weights, checkpoints, and caches
- local runtime folders such as `.runtime/` and `.venv/`

The default `.gitignore` excludes common output and cache locations, but it is
still your responsibility to review staged files before committing.

## Reporting Issues

If you discover a security or privacy issue, please open a minimal report that
does not include sensitive documents, private images, credentials, or proprietary
model files.
