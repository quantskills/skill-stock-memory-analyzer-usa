# Primary-source industry refresh implementation plan

> **For Codex:** Execute this plan sequentially in the current workspace. Preserve the existing uncommitted credential-window changes, use `apply_patch` for edits, and follow red-green-refactor for every behavior change.

**Goal:** Require a newly verified, traceable GPU/HBM industry snapshot before every stock analysis, with China/global official-source redundancy and an explicit one-run old-snapshot fallback when refresh fails.

**Architecture:** The Skill uses its web tools to discover and read current first-party pages, then writes a candidate JSON file. `utils/industry_refresh.py` deterministically validates the candidate, enforces official-domain and fact/estimate contracts, atomically promotes valid snapshots, creates a ticker-bound one-run manifest, and overlays the five runtime modules onto the existing `industry_data.json`. `analyze.py` and both platform launchers refuse to request `panda_data` credentials until the manifest passes precheck. The report displays source dates, current-run verification, estimate assumptions, and cached authorization separately from the remaining static industry sections.

**Tech stack:** Python 3 standard library (`argparse`, `copy`, `datetime`, `json`, `pathlib`, `tempfile`, `urllib.parse`, `unittest`), PowerShell, Bash/AppleScript, existing Plotly HTML report generator.

---

## Task 1: Define the snapshot contract with failing validator tests

**Files:**

- Create: `tests/__init__.py`
- Create: `tests/fixtures/industry_candidate_valid.json`
- Create: `tests/test_industry_refresh.py`
- Create: `utils/industry_refresh.py`

**Step 1: Write failing tests**

Create a representative five-module fixture with:

- `gpu_specs` as a fact with official NVIDIA sources;
- `nvda_compute_revenue` as a fact with NVIDIA IR and SEC sources;
- `gpu_shipments`, `gpu_mix`, and `hbm_supply` as estimates with `inputs`, `formula`, `assumptions`, `limitations`, ranges, and official anchors;
- `published_at`, `as_of`, `accessed_at`, `verified_at`, `region`, `language`, and `evidence` on every source.

Test that the fixture passes and that validation rejects:

- any missing required module;
- fact data containing an undeclared estimate;
- an estimate missing inputs, formula, assumptions, limitations, or sources;
- a hostname that only contains an official domain, such as `nvidia.com.attacker.example`;
- a final redirect URL outside the allowlist;
- invalid dates, future verification timestamps beyond a small clock tolerance, malformed units, and model ratios outside the permitted sum tolerance;
- conflicting same-period facts that are not explicitly resolved;
- a timestamp-only candidate whose data and evidence are unchanged from an old snapshot.

Run:

```powershell
python -m unittest tests.test_industry_refresh -v
```

Expected: FAIL because the validator does not exist.

**Step 2: Implement the smallest validator**

In `utils/industry_refresh.py`, add:

- `REQUIRED_MODULES` and exact official-domain roots;
- `host_is_allowed(host)` using equality or a dot-boundary suffix;
- `validate_source(source)` including optional `final_url` revalidation;
- `validate_snapshot(candidate, previous=None, now=None)`;
- explicit `SnapshotValidationError` error codes that never include page bodies, credentials, or tokens;
- module-specific structural checks and estimate ratio/range checks;
- `single_source` only for a direct official product fact, never as a substitute for estimate assumptions.

Run the focused test again and keep iterating until green.

**Step 3: Refactor and verify**

Keep source-domain configuration immutable, error messages stable, and all date parsing timezone-aware.

Run:

```powershell
python -m unittest tests.test_industry_refresh -v
python -m py_compile utils/industry_refresh.py
```

## Task 2: Add atomic snapshot promotion and regional source selection

**Files:**

- Modify: `tests/test_industry_refresh.py`
- Modify: `utils/industry_refresh.py`

**Step 1: Write failing storage and selection tests**

Using `tempfile.TemporaryDirectory`, test that:

- a valid candidate is atomically written as `industry_snapshot.json`;
- the former current snapshot becomes `industry_snapshot.previous.json` only after successful validation;
- an invalid candidate leaves both files untouched;
- China/Asia failure permits the same publisher's global source and vice versa;
- selection uses latest `as_of`, then `published_at`, then authority priority—not response order;
- a stable GPU specification updates `verified_at` without changing `published_at` or `as_of`;
- an official mirror conflict with no deterministic resolution fails the module.

Expected: FAIL because persistence and selection APIs do not exist.

**Step 2: Implement persistence and selection**

Add:

- `select_latest_sources(candidates)` grouped by module and publisher;
- authority ranking `regulatory > company_ir > product_datasheet > company_news > regional_product_page` only as a same-period tie-breaker;
- `promote_snapshot(candidate, runtime_dir)` using a temporary file, flush, and `os.replace`;
- source metadata that preserves all corroborating URLs and records `selection_reason`;
- no network requests in the validator; the Skill supplies retrieved data and final URLs.

Run focused tests until green.

**Step 3: Add a safe CLI**

Expose:

```text
python utils/industry_refresh.py validate --candidate <json>
python utils/industry_refresh.py commit --candidate <json> --ticker MU
python utils/industry_refresh.py status
```

CLI output may contain module names, dates, domains, status, and error codes only. It must never print full page content or environment variables.

## Task 3: Implement the one-run manifest and explicit cached fallback

**Files:**

- Create: `tests/test_industry_gate.py`
- Modify: `utils/industry_refresh.py`

**Step 1: Write failing gate tests**

Test the following states:

- a successful commit creates `industry_run.json` bound to one `refresh_id` and ticker;
- missing, malformed, expired, wrong-ticker, or already-claimed manifests fail precheck;
- failed refresh does not create a fresh manifest;
- `authorize-current --refresh-id <failed-id> --ticker MU` requires an existing fully valid current snapshot and creates `cached-authorized` mode;
- cached authorization records the failed modules and old snapshot `as_of` values;
- authorization is never inferred from silence and cannot be reused by another ticker or run;
- `claim_run_manifest()` atomically marks the manifest used before analysis.

Expected: FAIL because manifest behavior does not exist.

**Step 2: Implement run-manifest APIs and CLI**

Add:

- `create_fresh_manifest()` after successful snapshot promotion;
- `authorize_current_snapshot()` only after the Skill has obtained an explicit user answer;
- `precheck_run_manifest(path, ticker)` with no credential access;
- `claim_run_manifest(path, ticker)` using atomic rename/write semantics;
- CLI commands `precheck` and `authorize-current`;
- short validity windows and a clear `cached-authorized` marker, without storing chat text or user identity.

Run:

```powershell
python -m unittest tests.test_industry_gate -v
```

## Task 4: Overlay runtime GPU/HBM data without mutating static config

**Files:**

- Modify: `tests/test_industry_refresh.py`
- Modify: `utils/industry_refresh.py`
- Modify: `utils/data_updater.py`

**Step 1: Write failing overlay and freshness tests**

Test that `apply_runtime_snapshot(base, snapshot)` deep-copies the base config and replaces only:

- `gpu_hbm_specs.generations`;
- `gpu_hbm_specs.nvda_quarterly_revenue`;
- `gpu_hbm_specs.asp_per_gpu_k_usd` and any shipment range inputs;
- `gpu_hbm_specs.gpu_mix_ratios`;
- `gpu_hbm_specs.hbm_supply_params`.

Also verify DRAM, NAND, downstream, CapEx, technology-node, peer, and company-profile sections remain byte-equivalent in meaning. Test that `get_data_freshness(snapshot=...)` uses per-module `verified_at` and status instead of `gpu_hbm_specs._last_updated`.

Expected: FAIL with current static-only behavior.

**Step 2: Implement the overlay adapter**

Translate the stable snapshot schema into the legacy keys consumed by `utils/memory_analyzer.py` and the backtester. Attach provenance under a separate runtime metadata key so analytical arrays never mix with source records.

**Step 3: Fix freshness semantics**

Update `utils/data_updater.py` so the five runtime modules report `fresh`, `cached-authorized`, or `failed` independently. Stable specs verified during this run remain fresh even when their original publication date is old. Other static industry sections retain their existing age rules.

## Task 5: Enforce the gate in `analyze.py`

**Files:**

- Create: `tests/test_analyze_industry_gate.py`
- Modify: `analyze.py`

**Step 1: Write failing CLI and entrypoint tests**

Patch heavy dependencies and assert that:

- normal analysis without `--industry-run-manifest` exits before `run_preflight()` and before any `panda_data` call;
- a valid fresh manifest is claimed, its snapshot is overlaid, and analysis proceeds;
- a cached-authorized manifest proceeds with an explicit warning;
- invalid or reused manifests do not ask for credentials and do not create HTML;
- `--check-deps` and the new industry `precheck` path never inspect credentials.

Expected: FAIL because the current entrypoint has no industry gate.

**Step 2: Implement the entrypoint changes**

Add `--industry-run-manifest`, require it for ticker analysis, and perform this order:

1. validate ticker and period;
2. precheck and claim the run manifest;
3. load and overlay the runtime industry snapshot;
4. only then run credential/network preflight;
5. generate the report with snapshot metadata.

Remove the current generic “WebSearch 后更新 `industry_data.json`” warning for GPU/HBM runtime modules. Do not weaken existing dependency or credential protections.

## Task 6: Show source quality, estimates, and cached authorization in HTML

**Files:**

- Create: `tests/test_report_industry_snapshot.py`
- Modify: `utils/report_builder.py`
- Modify: `utils/memory_analyzer.py`

**Step 1: Write failing report tests**

Render minimal reports and assert escaped HTML contains:

- each module's fact/estimate label;
- `published_at`, `as_of`, `verified_at`, and official source links;
- formulas, major assumptions, limitations, range, and confidence for estimates;
- a top-level and HBM-adjacent warning for `cached-authorized` mode;
- no “9 days old” warning for a GPU specification verified this run;
- no unqualified wording that presents GPU shipment, model mix, HBM supply, or exact shortage as an official fact.

Expected: FAIL with the current report.

**Step 2: Add report snapshot components**

Pass `industry_snapshot` and `industry_run_mode` into `build_report()`. Add a compact provenance panel and a cached-data banner. Escape all source text and URLs before interpolation.

**Step 3: Qualify model conclusions**

Update `utils/memory_analyzer.py` output strings and structures so estimate results use ranges and phrases such as “模型估算” and “在当前假设下”. Remove hard-coded unsupported supply assertions from generated assessments.

## Task 7: Gate both visible credential launchers before prompting

**Files:**

- Create: `tests/test_launcher_contract.py`
- Modify: `scripts/run_with_prompt.ps1`
- Modify: `scripts/run_with_prompt.sh`
- Modify: `.gitattributes`

**Step 1: Write failing launcher contract tests**

Use text/static contract tests plus subprocess checks available on the current platform to verify:

- both launchers require an industry manifest argument;
- both call `industry_refresh.py precheck` before `Read-Host` or `read -s`;
- neither puts account/password values on the command line or in the status file;
- invalid precheck exits before credential input;
- PowerShell remains visible and macOS continues to use Terminal.app;
- exit codes distinguish industry gate failure from dependency and login failures.

Expected: FAIL before launcher modifications.

**Step 2: Modify launchers**

Add `-IndustryRunManifest` / `--industry-run-manifest`, pass the path without credentials, call gate precheck before dependency and credential prompts, then pass the manifest to `analyze.py`. Preserve current password hiding and cleanup. Add `*.ps1 text eol=crlf` while retaining `*.sh text eol=lf`.

## Task 8: Rewrite the Skill workflow and user documentation

**Files:**

- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `README.en.md`

**Step 1: Add behavior-oriented Skill checks**

Extend `tests/test_launcher_contract.py` or add `tests/test_skill_contract.py` to require that `SKILL.md`:

- lists supported tickers before analysis when no ticker is selected;
- refreshes the five modules from official China/global sources before opening the credential window;
- records direct facts separately from estimates;
- asks exactly once for explicit old-data permission after refresh failure;
- stops when the user refuses, does not answer, or no valid snapshot exists;
- invokes the correct validator/commit/authorization/launcher commands;
- never asks for credentials in chat.

Expected: FAIL before documentation changes.

**Step 2: Update `SKILL.md`**

Replace the current “登录前不浏览网页补数” behavior with:

1. select one ticker;
2. announce official-source refresh;
3. search the allowlisted regional/global official entrypoints and write the candidate fixture shape;
4. validate and commit it;
5. on failure, show affected modules and old dates, then request explicit permission;
6. only after fresh commit or authorization, open the visible local credential window;
7. inspect and deliver the generated HTML.

Include the candidate JSON template, current official source catalog, exact commands, error handling, and credential-safe logging rules.

**Step 3: Update both READMEs**

Document the same order for beginners: choose ticker, refresh public industry data, decide on old data only if necessary, complete local hidden-password login, and open the HTML report. Clarify that the Skill—not the user—normally prepares the candidate snapshot.

## Task 9: Full verification and clean handoff

**Files:**

- Verify all modified files
- Do not add anything under `output/`

**Step 1: Run the complete offline suite**

```powershell
python -m unittest discover -s tests -v
python -m py_compile analyze.py utils/industry_refresh.py utils/data_updater.py utils/memory_analyzer.py utils/report_builder.py utils/preflight.py
python analyze.py --check-deps
git diff --check
```

**Step 2: Run non-credential smoke checks**

Validate and commit a fixture into a temporary runtime directory, exercise fresh and authorized manifests, and verify a third-party URL is rejected. Do not open a credential window or call `panda_data` during automated verification.

**Step 3: Review security and workspace scope**

Confirm with `rg` that no account, password, token, prior user credential, generated HTML, candidate runtime file, or output snapshot is staged. Review all logging and exception paths for secret leakage.

**Step 4: Commit in bounded units**

Stage only files belonging to this implementation. Suggested commits:

```text
feat: 新增一手行业数据快照门禁
feat: 在报告展示行业数据来源与估算
docs: 更新分析前数据刷新流程
```

Do not push until requested or already authorized for the target branch in the active conversation.
