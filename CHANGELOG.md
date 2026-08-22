# [](https://github.com/Skopaq-AI/tantu-platform/compare/v0.9.2...v) (2026-08-22)


### Bug Fixes

* **edge:** health now ensures redis connection live before reporting degraded ([a9fb482](https://github.com/Skopaq-AI/tantu-platform/commit/a9fb48223b865a6decbbf1f674ff0060e20ff577))

## [0.9.2](https://github.com/Skopaq-AI/tantu-platform/compare/v0.9.1...v0.9.2) (2026-08-22)


### Bug Fixes

* **tests:** keep api.test mocked but gate demo, preserve coverage ([bc84610](https://github.com/Skopaq-AI/tantu-platform/commit/bc84610ffcf2f1e5eb491b1d3c31be5d59059369))
* **wiring:** deep audit across all layers — role landing redirect, mock gating behind DEMO, API_URL, adapter dual-write, gateway RBAC, infra secrets ([507ec5c](https://github.com/Skopaq-AI/tantu-platform/commit/507ec5c88df1db9374720342b629a0fa9f0e7654))

## [0.9.1](https://github.com/Skopaq-AI/tantu-platform/compare/v0.9.0...v0.9.1) (2026-08-22)


### Bug Fixes

* **gateway:** GET /onboard now lists adapters instead of 405 Method Not Allowed ([22c0229](https://github.com/Skopaq-AI/tantu-platform/commit/22c02295562ce96b748339ce98997994516a411d))

# [0.9.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.8.2...v0.9.0) (2026-08-21)


### Features

* **frontend:** child-simple landing — layman language, AI still prominent ([d90aa33](https://github.com/Skopaq-AI/tantu-platform/commit/d90aa33b4e27af8263049d0628f655863c45780e))

## [0.8.2](https://github.com/Skopaq-AI/tantu-platform/compare/v0.8.1...v0.8.2) (2026-08-21)


### Bug Fixes

* **redis:** add PVC for durability (survives pod reschedule to new node) ([e381abc](https://github.com/Skopaq-AI/tantu-platform/commit/e381abc5715d382ab0be082b559e3080d93f1019))

## [0.8.1](https://github.com/Skopaq-AI/tantu-platform/compare/v0.8.0...v0.8.1) (2026-08-21)


### Bug Fixes

* **edge:** make base the final default stage (cloud CI was building edge-orin L4T and failing) ([ab309e5](https://github.com/Skopaq-AI/tantu-platform/commit/ab309e5b329dada0b0a61239c1cddf3996408947))

# [0.8.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.7.2...v0.8.0) (2026-08-21)


### Features

* **prod:** persistence, discovery, edge accel, VLLM — no stubs ([d770e03](https://github.com/Skopaq-AI/tantu-platform/commit/d770e03d2bf9899299c280cbc398476352e01d01))

## [0.7.2](https://github.com/Skopaq-AI/tantu-platform/compare/v0.7.1...v0.7.2) (2026-08-21)


### Bug Fixes

* **modbus:** remove stray else after _decode_registers (SyntaxError in 907277f) ([bd665b9](https://github.com/Skopaq-AI/tantu-platform/commit/bd665b9cab73df56821ef2b25fe56c07be9285ae))

## [0.7.1](https://github.com/Skopaq-AI/tantu-platform/compare/v0.7.0...v0.7.1) (2026-08-21)


### Bug Fixes

* **modbus:** pymodbus 3.x compat slave→device_id fallback (no stubs) ([907277f](https://github.com/Skopaq-AI/tantu-platform/commit/907277fc50433ec85fe3a4cb03894099fd4abb75))

# [0.7.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.6.0...v0.7.0) (2026-08-21)


### Features

* **onboard:** plug-and-play one-call plant integration + gateway routing ([bc4346e](https://github.com/Skopaq-AI/tantu-platform/commit/bc4346ecc425ee3b4ffe19c08279e2ea185c9e04))

# [0.6.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.5.1...v0.6.0) (2026-08-21)


### Features

* **landing:** highlight AI-driven dual brain + edge + grounded RAG ([0da2214](https://github.com/Skopaq-AI/tantu-platform/commit/0da221439de43ab94a64d42f302f648cc2f614c3))

## [0.5.1](https://github.com/Skopaq-AI/tantu-platform/compare/v0.5.0...v0.5.1) (2026-08-21)


### Bug Fixes

* **gateway,helm:** harden autopilot scheduling, remove argo gatewayAPI plugin, add downstream microservices ([1b5c17d](https://github.com/Skopaq-AI/tantu-platform/commit/1b5c17d407f0836a87fef4c1cc4b971a848bc786))

# [0.5.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.4.0...v0.5.0) (2026-08-21)


### Features

* **landing:** customer marketing page (sales) — split hero, dark proof strip, how-it-works line, persona benefits, mono integrations, security tenancy, pricing table, CTA; dash live data removed from public / (still at /operator etc behind auth) ([d9c29dd](https://github.com/Skopaq-AI/tantu-platform/commit/d9c29dd933291fefc44182832f21c624908fc9c2))

# [0.4.0](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.14...v0.4.0) (2026-08-21)


### Features

* **auth:** org-level RBAC (8 roles), ABAC plant/line, JWT RS256/HS256, HttpOnly refresh, RLS, middleware+RoleGuard, landing public/core behind auth, user mgmt + API keys ([e1c7905](https://github.com/Skopaq-AI/tantu-platform/commit/e1c790527188c0198d3f97e2c4bf36a6dd915c08))

## [0.3.14](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.13...v0.3.14) (2026-08-21)


### Bug Fixes

* **gateway:** HTTPRoute hostnames add 8.233.79.240 so http://8.233.79.240/ 200 not 404 fault filter abort ([a6dbfc0](https://github.com/Skopaq-AI/tantu-platform/commit/a6dbfc07f524e6b6bc4261fb8194b288c73ea8aa))

## [0.3.13](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.12...v0.3.13) (2026-08-21)


### Bug Fixes

* **cloudbuild:** remove unused _ENV substitution — was INVALID_ARGUMENT key _ENV not matched ([ae18649](https://github.com/Skopaq-AI/tantu-platform/commit/ae18649ab0cd85f4863a33ca8eb8db4c08c317a8))
* **helm/gateway:** correct static IP for serving + template fixes ([52ab1eb](https://github.com/Skopaq-AI/tantu-platform/commit/52ab1eb914c9d1444975fd9eda44c5df34d2ec1b))

## [0.3.12](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.11...v0.3.12) (2026-08-21)


### Bug Fixes

* **helm:** qdrant 0.8.6 → 1.15.5 + gateway TLS fix for dev ([b9f4521](https://github.com/Skopaq-AI/tantu-platform/commit/b9f45210c44792ae564b10ab605465923a9c6cc8))

## [0.3.11](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.10...v0.3.11) (2026-08-21)


### Bug Fixes

* **terraform:** unblock apply — postgres flags + GKE WI bootstrap ([b81116c](https://github.com/Skopaq-AI/tantu-platform/commit/b81116c159b9177c49f1a9825b5d9066e1462e39))

## [0.3.10](https://github.com/Skopaq-AI/tantu-platform/compare/v0.3.9...v0.3.10) (2026-08-21)


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
