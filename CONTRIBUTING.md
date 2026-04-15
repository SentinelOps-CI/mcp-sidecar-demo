# Contributing

Thank you for helping improve this project. Please keep changes focused and covered by checks where practical.

## Setup

```bash
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

## Before you open a PR

```bash
make ci
```

Optionally, on Linux or macOS with a suitable toolchain:

```bash
make race
```

## Guidelines

- Match existing style and keep diffs easy to review.
- Add or extend tests when behavior changes (`tests/` for Python, `sidecar/*_test.go` for Go).
- Do not commit secrets, API keys, or `instance_info.json` (see `.gitignore`).
- Update [README.md](README.md) when user-visible behavior changes.

Use [.github/pull_request_template.md](.github/pull_request_template.md) when opening pull requests.

## License

Contributions are licensed under the same terms as the project ([LICENSE](LICENSE)).
