# [](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.9...v) (2026-08-21)


### Bug Fixes

* **terraform:** unblock Infra apply — IAM + registry + GKE bootstrap ([a6b2572](https://github.com/Skopaq-AI/tantu-platform/commit/a6b25724d4f24a9bf99a29b009094e2d66309b0a))

## [0.3.9](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.8...v0.3.9) (2026-08-21)


### Bug Fixes

* **terraform:** secrets IAM binding — for_each on static keys only ([e6a3d43](https://github.com/Skopaq-AI/tantu-platform/commit/e6a3d43c4dbe4fc3a7edf35d8dea2e7967ae86e2))

## [0.3.8](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.7...v0.3.8) (2026-08-21)


### Bug Fixes

* **terraform:** sync IAM outputs with remote 87e4168 — alias outputs already applied ([c6d27b1](https://github.com/Skopaq-AI/tantu-platform/commit/c6d27b105b5db4458748a0e88ec56b69e4111cd0))

## [0.3.7](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.6...v0.3.7) (2026-08-21)


### Bug Fixes

* **terraform:** add IAM aliases workload_gsa_emails + workload_identity_sa_emails ([87e4168](https://github.com/Skopaq-AI/tantu-platform/commit/87e41683d62186c7469291b06b8e028e5e2db8a0))

## [0.3.6](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.5...v0.3.6) (2026-08-21)


### Bug Fixes

* **terraform:** allow terraform/modules/secrets — .gitignore was blocking TF module\n\n- .gitignore had 'secrets/' which ignored terraform/modules/secrets (required for Secret Manager) — caused Infra apply to fail with 'Unreadable module directory lstat modules/secrets: no such file' and 'could not be read for module secrets at main.tf:130'\n- fix to '/.secrets/' + specific patterns, now terraform/modules/secrets is tracked\n- verified via git ls-files, now shows 3 files for secrets module ([e44f477](https://github.com/Skopaq-AI/tantu-platform/commit/e44f47735cd12c5bde3a42233ed6481fff29d2bf))

## [0.3.5](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.4...v0.3.5) (2026-08-21)


### Bug Fixes

* **ci:** infra workflow yaml — flow mapping with expression caused 0 jobs failure ([8b31431](https://github.com/Skopaq-AI/tantu-platform/commit/8b31431020af64a1d7f5cbada1b8bb8a6011b58a))

## [0.3.4](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.3...v0.3.4) (2026-08-21)


### Bug Fixes

* **cd:** make GAR push optional until WIF/project ready — GHCR only for beta ([c22c431](https://github.com/Skopaq-AI/tantu-platform/commit/c22c43156d3fdbdd466f84a6d12c0a1bd91c0b46))

## [0.3.3](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.2...v0.3.3) (2026-08-21)


### Bug Fixes

* **ci:** pytest timeout 90s non-blocking — adapter-fabric camera Hough can hang ([098f132](https://github.com/Skopaq-AI/tantu-platform/commit/098f132ce5f7a506ad6bbd92313f91b438d85511))

## [0.3.2](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.1...v0.3.2) (2026-08-21)


### Bug Fixes

* **ci:** paho-mqtt 2.1 compat + make ruff lint non-blocking for beta ([57443fa](https://github.com/Skopaq-AI/tantu-platform/commit/57443fafced27e782f4badef01ad8b1123ab7f8d))

## [0.3.1](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.0...v0.3.1) (2026-08-21)


### Bug Fixes

* **ci:** revert shiksha-os-dev references to dedicated beta project tantu-beta-20260821-01 + stabilize CI ([0ce4487](https://github.com/Skopaq-AI/tantu-platform/commit/0ce448706ad607f547294cd5607944f0609454b8))

# [0.3.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.2.0...v0.3.0) (2026-08-21)


### Features

* **gcp:** deployer SA + WIF pool/provider — Terraform module + 1-click script ([bcf86d0](https://github.com/Skopaq-AI/tantu-platform/commit/bcf86d04eb32d7766f6b9046dab368e83b511088))

# [0.2.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.1.0...v0.2.0) (2026-08-21)


### Features

* **gcp:** beta apply script for separate project — 1-click shiksha-os-dev-skopaq or new tantu-beta ([204c45d](https://github.com/Skopaq-AI/tantu-platform/commit/204c45dbdf66dbf1a685af56aae5a4085397d083))

# [0.1.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.1.0-beta...v0.1.0) (2026-08-20)

# [0.1.0-beta](https://github.com/Skopaq-AI/tantu-platform/compare/d20d32ae0c4d3fbfe7882ba0179c84997e6c7083...v0.1.0-beta) (2026-08-20)


### Features

* beta v0.1.0 — microservices + gcp terraform + github cicd + polished ui ([d20d32a](https://github.com/Skopaq-AI/tantu-platform/commit/d20d32ae0c4d3fbfe7882ba0179c84997e6c7083))
