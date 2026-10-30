# End-to-End Repository Scan Validation

**Date:** 2026-10-30  
**Result:** Live frontend-to-API scans succeeded for two public repositories. Edge-case responses were also exercised against the live API. This validates the tested Java scans, not all Java syntax or every possible repository.

## Live Application

- Frontend: `http://127.0.0.1:5173/scanner`
- API: `http://127.0.0.1:8000/scan-repo`
- Actual frontend workflow: enter the repository URL in the Scanner page and select **Scan Repository**. The browser issued `POST http://localhost:8000/scan-repo` with `{"url":"..."}` and rendered returned file risk, LOC, churn, and revisions.
- API loading: each scan loaded the existing `RandomForest_combined.pkl`, `scaler.pkl`, and training imputer medians. No training pipeline or model was changed for this validation.

## Public Repository Scans

### Ordinary Repository

**URL:** `https://github.com/kevinsawicki/http-request.git`  
**Scanned commit:** `2d62a3e9da726942a93cf16b6e91c0187e6c0136`  
**Request:** `POST /scan-repo` with `{"url":"https://github.com/kevinsawicki/http-request.git"}`  
**Response:** HTTP 200; four Java files discovered, four file-level vectors returned, 13 declarations discovered, four source identities scored, nine additional declarations not individually scored, zero parser/analysis failures, 137 unresolved project references.

The frontend displayed four result rows. The API returned:

| File / FQCN | LOC | WMC | DIT | NOC | RFC | LCOM5 | CBO | NPA | NPM | NLE | CBOI | CD | Churn | Revisions | Developers | Probability / risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `HttpRequestTest.java` / `com.github.kevinsawicki.http.HttpRequestTest` | 3606 | 163 | 1 | 0 | 309 | 0.169753 | 25 | 0 | 163 | 2 | 0 | 0.220466 | 9329 | 98 | 7 | 0.097909 / LOW |
| `HttpRequest.java` / `com.github.kevinsawicki.http.HttpRequest` | 3162 | 189 | 0 | 0 | 200 | 0.990078 | 47 | 30 | 145 | 9 | 1 | 0.480392 | 11553 | 226 | 12 | 0.080000 / LOW |
| `ServerTestCase.java` / `com.github.kevinsawicki.http.ServerTestCase` | 160 | 3 | 0 | 1 | 25 | 1.083333 | 11 | 0 | 3 | 1 | 1 | 0.243750 | 452 | 9 | 2 | 0.050716 / LOW |
| `EncodeTest.java` / `com.github.kevinsawicki.http.EncodeTest` | 74 | 2 | 0 | 0 | 3 | 0 | 0 | 0 | 2 | 0 | 0 | 0.081081 | 200 | 3 | 1 | 0.041139 / LOW |

### Multi-Package Repository with Inheritance and Renames

**URL:** `https://github.com/iluwatar/java-design-patterns.git`  
**Scanned commit:** `4cabb204f240240bea319605a5ffa46ded728001`  
**Request:** `POST /scan-repo` with `{"url":"https://github.com/iluwatar/java-design-patterns.git"}`  
**Response:** HTTP 200; 2,042 Java files discovered and file-level feature vectors computed; 2,080 source declarations discovered; 1,881 file rows had a source-level primary-class identity; 161 file rows had no identified class; 38 additional declarations were not individually scored; 82 context parser failures; zero file feature-extraction exceptions; 4,631 unresolved project references. The API returned the top 50 files by predicted probability and the frontend rendered the ranked results.

Representative returned results:

| File / FQCN | LOC | WMC | DIT | NOC | RFC | LCOM5 | CBO | NPA | NPM | NLE | CBOI | CD | Churn | Revisions | Developers | Probability / risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `promise/.../Promise.java` / `com.iluwatar.promise.Promise` | 159 | 9 | 1 | 0 | 15 | 0.812500 | 9 | 0 | 7 | 1 | 4 | 0.314465 | 590 | 18 | 7 | 0.551115 / HIGH |
| `hexagonal-architecture/.../InMemoryBankTest.java` / `com.iluwatar.hexagonal.banking.InMemoryBankTest` | 16 | 1 | 0 | 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 122 | 15 | 8 | 0.536537 / HIGH |
| `repository/.../Person.java` / `com.iluwatar.repository.Person` | 14 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 7 | 0.071429 | 430 | 20 | 12 | 0.515193 / HIGH |
| `layered-architecture/.../CakeBakingService.java` / `service.CakeBakingService` | 26 | 9 | 0 | 1 | 9 | 0 | 5 | 0 | 0 | 0 | 4 | 0.230769 | 382 | 21 | 8 | 0.511764 / HIGH |

`Promise` demonstrates resolved inheritance depth (DIT=1). Multiple package-qualified identities appeared in both the API rows and the all-file verification matrix.

### Renamed File History

Native Git history for this same scanned repository records a cross-directory Java move at commit `6cd2d0353a40d132a4945c09a28ee70580408f72`:

`hexagonal/src/main/java/com/iluwatar/hexagonal/banking/InMemoryBank.java` → `hexagonal-architecture/src/main/java/com/iluwatar/hexagonal/banking/InMemoryBank.java`

The rename commit is an ancestor of the scanned commit. Native `git log --follow --find-renames` reports churn 219, 19 revisions, and 10 developers at the scanned commit. The independently extracted current-path row matches those Git values and has identity `com.iluwatar.hexagonal.banking.InMemoryBank`, LOC 30, WMC 3, DIT 0, NOC 0, RFC 6, LCOM5 1.5, CBO 3, NPA 0, NPM 3, NLE 1, CBOI 2, CD 0, probability 0.119072 (LOW). It was processed by the API but not included in the returned top 50 because of its lower score; the API intentionally truncates its displayed result list to 50.

## Feature and Model Validation

The full local replay at the API-reported rich-repository commit produced a `2042 × 15` feature matrix in the trained feature order. All feature cells were numeric and finite; there were zero missing feature cells. Feature values varied across files; for example, churn ranged across 461 unique values and revisions across 35 unique values. Evolution features for an incomplete history correctly reflected only history available in that clone. The API computes one prediction for every file but returns only its top 50; all 50 returned vectors and probabilities were compared against the independent full local replay (zero differences). The other 1,992 file rows were validated in the local replay, not directly compared to an API response because they are not included in that response.

The API's returned top-50 feature vectors and probabilities matched the full local replay exactly: **50 rows compared, zero differences**. The replay used the same `extract_repository_features`, saved training medians, saved scaler, saved model, and positive-class probability column. The full matrix is in [java_design_patterns_scored_files.csv](../data/repository_scan_integration/java_design_patterns_scored_files.csv); aggregate checks are in [java_design_patterns_scan_summary.json](../data/repository_scan_integration/java_design_patterns_scan_summary.json).

The scanner returns one primary file-level prediction, not a separate prediction for every declaration in a multi-class file. It reports `classes_scored`, `non_primary_classes_not_scored`, and `unidentified_class_files`; it does not pretend those unscored declarations have valid class identities.

## Incomplete History

A depth-1 clone of `https://github.com/kevinsawicki/http-request.git` was confirmed shallow before submission. The live API returned HTTP 200 at commit `2d62a3e9da726942a93cf16b6e91c0187e6c0136`, discovered four Java files, and reported `HttpRequest.java` with churn 3,259, revision count 1, and developer count 1. This is the history present in the shallow checkout, not the full-repository history (full history reports 11,553 / 226 / 12 for that file). The scanner does not fabricate the missing history, but users must interpret these evolution metrics as incomplete.

## Safe Error and Unsupported-Syntax Behavior

| Case | Actual request | HTTP | Observed response |
|---|---|---:|---|
| Invalid URL | `{"url":"not-a-valid-repository"}` | 400 | Invalid repository URL/path detail; no scan performed. |
| Clone failure | `file:///.../missing-repository.git` | 400 | Git clone failure detail returned; temp checkout cleaned. |
| Empty repository, no commit | `file:///.../empty-repository` | 200 | No Java files message, null commit, zero files/classes, empty results. |
| Unsupported Java record syntax | Local committed `ModernRecord.java` | 200 | One file-level result; one parser-context failure and one unidentified class file are reported. The class FQCN is blank; regex fallback produces LOC 1, WMC 1, RFC 1, CBO 1, NPM 1 and Git metrics 1/1/1. Probability is valid and may be 0.0. |

Unsupported syntax is not silently described as AST success. In the rich public repository, 82 context parse failures consisted of 81 `JavaSyntaxError` cases and one lexer failure on a text block; 79 other unidentified files had no uniquely resolved class/interface identity (including enum/package-info-style files). No file-level analysis exception occurred, but their fallback/class-identity limitations are reported.

## Evidence Files

- [Live API requests and response payloads](../data/repository_scan_integration/live_api_evidence.json)
- [Final frontend response summary](../data/repository_scan_integration/final_frontend_response_summary.json)
- [Full rich-repository scored matrix](../data/repository_scan_integration/java_design_patterns_scored_files.csv)
- [Matrix verification summary](../data/repository_scan_integration/java_design_patterns_scan_summary.json)

## Automated Tests

The final repository test suite passed **21 tests in 48.7 seconds**. This includes API response metadata, invalid URL, clone failure, empty no-commit repository, unsupported Java record syntax, training/scanning parity, and qualified-identity regressions. Non-failing Starlette/httpx deprecation and sklearn feature-name warnings were observed.

## Verdict

**End-to-end scanning is verified for the tested requests:** the real scanner page submitted public URLs, FastAPI cloned them, extracted features, loaded the existing scaler/model, produced probabilities, and rendered ranked results. The tested normal scans had zero file extraction exceptions, and the rich repository's returned API rows matched the independent full-matrix replay exactly.

This does **not** establish support for all Java syntax or all declarations. In particular, 161 rich-repository file rows lacked a resolved source-level identity, 82 files failed the context parser, only one primary declaration per file is predicted, and shallow history undercounts evolution features. Treat these as explicit scan limitations rather than claiming universal per-class coverage.
