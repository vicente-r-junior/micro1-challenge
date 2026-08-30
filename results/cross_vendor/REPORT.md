# Results: behavioural parity, baseline vs agent

Model `openai/gpt-4o-mini` · 16 cases · live run

## What is measured

The routes of each legacy Flask module are read statically, a fixed set of HTTP requests is derived from them, and those exact requests are replayed against the Flask app and against the migrated FastAPI app. **The Flask responses are the specification.** No language model judges anything.

**Primary metric — migrations that are shippable.** The share of cases where *every* probe reproduces the legacy status and body. This is the number that decides whether a migration can be merged: nobody deploys 92% of a service. A single unmatched probe is a live client breaking.

**Cost and model time** are what the recorded run actually spent. Replaying is free and finishes in seconds; the columns describe the work, not the cache. Model time is the summed latency of every call, so it is comparable across variants even when some of them were served from the cache.

**Secondary metric — mean behavioural parity.** How close the non-shippable migrations are. Useful for seeing progress; not a release criterion.

**What is not compared.** One class of probe is scored on its status code alone: those where the legacy app answered with the framework's own HTML error page, which no migration can reproduce. The count appears below so the relaxation is visible rather than assumed. Every other body — JSON, CSV, plain text — is compared in full.

| Variant | What it adds | **Shippable** | Mean parity | LLM calls | Cost (USD) | Model time |
|---|---|---|---|---|---|---|
| `v0_baseline` | single prompt (baseline) | **1/14** (7%) | 42.9% | 16 | 0.0062 | 1 min |
| `v2_repair` | + tool-calling repair loop | **5/15** (33%) | 72.7% | 64 | 0.0381 | 4 min |

## Headline

Shippable migrations go from **1/14** with a single prompt to **5/15** with the full agent — +4 cases, +27% of the benchmark.

Mean parity moves 42.9% → 72.7%. The mean moves less than the shippable count, and that is the point: the baseline is already *nearly* right almost everywhere. The value is not in the average, it is in closing the last few probes — which are the ones that break production and which no code review catches.

## Per case

`100%` means every probe matched — the migration is shippable. Anything else is an observable behaviour change.

| Case | `v0_baseline` | `v2_repair` |
|---|---|---|
| case_01_inventory | 40% | 67% |
| case_02_blueprint_auth | 29% | 57% |
| case_03_app_config | 55% | 82% |
| case_04_error_handlers | 20% | 50% |
| case_05_response_shapes | 62% | 77% |
| case_06_query_params | 67% | **100%** |
| case_07_path_converters | 46% | **100%** |
| case_08_method_view | 29% | **100%** |
| case_09_bulk_status | 0% | **100%** |
| case_10_conditional_update | 36% | 82% |
| case_11_trailing_slash | **100%** | **100%** |
| case_12_pagination_headers | — | — |
| case_13_restful_todo | — | 47% |
| case_14_restful_todo_simple | 33% | 56% |
| case_15_inconsistent_errors | 61% | 0% |
| case_16_state_machine | 23% | 73% |

## By provenance

The synthetic cases were written for this benchmark by the author of the tool. The third-party cases are real code, vendored unmodified. They are scored identically and reported separately because a benchmark you designed yourself is the one you should trust least.

| Variant | Synthetic (shippable) | Third-party (shippable) |
|---|---|---|
| `v0_baseline` | 1/13 | 0/1 |
| `v2_repair` | 5/13 | 0/2 |

## Agent behaviour (`v2_repair`)

- Cases needing repair: 12/15
- Repair turns when used: 2–8 (budget 8)
- Tool calls: `get_probe_detail` ×51, `run_differential` ×8, `search_legacy` ×20, `submit` ×1
- Lessons in the ledger at the end: 0
- Probes scored on status alone (framework error pages): 44/208
- Concurrency: 4 workers, wave size 16
