# Results: behavioural parity, baseline vs agent

Model `deepseek/deepseek-v4-pro` · 16 cases · live run

## What is measured

The routes of each legacy Flask module are read statically, a fixed set of HTTP requests is derived from them, and those exact requests are replayed against the Flask app and against the migrated FastAPI app. **The Flask responses are the specification.** No language model judges anything.

**Primary metric — migrations that are shippable.** The share of cases where *every* probe reproduces the legacy status and body. This is the number that decides whether a migration can be merged: nobody deploys 92% of a service. A single unmatched probe is a live client breaking.

**Cost and model time** are what the recorded run actually spent. Replaying is free and finishes in seconds; the columns describe the work, not the cache. Model time is the summed latency of every call, so it is comparable across variants even when some of them were served from the cache.

**Secondary metric — mean behavioural parity.** How close the non-shippable migrations are. Useful for seeing progress; not a release criterion.

**What is not compared.** One class of probe is scored on its status code alone: those where the legacy app answered with the framework's own HTML error page, which no migration can reproduce. The count appears below so the relaxation is visible rather than assumed. Every other body — JSON, CSV, plain text — is compared in full.

| Variant | What it adds | **Shippable** | Mean parity | LLM calls | Cost (USD) | Model time |
|---|---|---|---|---|---|---|
| `v0_baseline` | single prompt (baseline) | **11/16** (69%) | 86.4% | 16 | 0.7210 | 45 min |

## Per case

`100%` means every probe matched — the migration is shippable. Anything else is an observable behaviour change.

| Case | `v0_baseline` |
|---|---|
| case_01_inventory | **100%** |
| case_02_blueprint_auth | 71% |
| case_03_app_config | **100%** |
| case_04_error_handlers | **100%** |
| case_05_response_shapes | **100%** |
| case_06_query_params | **100%** |
| case_07_path_converters | **100%** |
| case_08_method_view | **100%** |
| case_09_bulk_status | **100%** |
| case_10_conditional_update | 73% |
| case_11_trailing_slash | **100%** |
| case_12_pagination_headers | 75% |
| case_13_restful_todo | 29% |
| case_14_restful_todo_simple | 33% |
| case_15_inconsistent_errors | **100%** |
| case_16_state_machine | **100%** |

## By provenance

The synthetic cases were written for this benchmark by the author of the tool. The third-party cases are real code, vendored unmodified. They are scored identically and reported separately because a benchmark you designed yourself is the one you should trust least.

| Variant | Synthetic (shippable) | Third-party (shippable) |
|---|---|---|
| `v0_baseline` | 11/14 | 0/2 |
