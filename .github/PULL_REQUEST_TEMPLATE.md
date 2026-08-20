<!--- Conventional Commit title required: feat|fix|docs|chore|ci|refactor|perf|test(scope): summary -->

## Summary

<!-- What + why. Link issue if any. -->

## Type

- [ ] feat (minor bump)
- [ ] fix/perf/refactor (patch bump)
- [ ] BREAKING CHANGE (major bump — describe below)
- [ ] chore/docs/ci (no release)

## Checklist

- [ ] Title follows Conventional Commits (`feat(adapter): ...`)
- [ ] `ruff check` + `mypy` + `pytest` green (or CI will gate)
- [ ] Frontend `npm run lint` + `vitest` green (if touched)
- [ ] No secrets committed (`gitleaks` will gate)
- [ ] Updated `docs/` / ADR if architecture changed
- [ ] Tested via `docker compose -f docker-compose.microservices.yml up --build`

## Notes for reviewer

<!-- risk, rollback, infra impact -->
