## Summary

- Why this change is necessary.
- Key design and implementation decisions.
- Any intentional behavior change (including policy or security semantics).

## Verification

- [ ] `make ci`
- [ ] `cd sidecar && go test ./...`
- [ ] If provisioning changed: run `make setup` and `make test` in a Morph-enabled environment
- [ ] If supported: `make race`

## Documentation

- [ ] [README.md](../README.md) updated for user-visible changes
- [ ] [CONTRIBUTING.md](../CONTRIBUTING.md) updated if contributor workflow changed

## Risk review

- [ ] Policy behavior unchanged or explicitly documented
- [ ] Auth and trust assumptions still valid
- [ ] Audit paths validated if touching auth or logging (token redaction)
- [ ] No secrets or `instance_info.json` in the diff
