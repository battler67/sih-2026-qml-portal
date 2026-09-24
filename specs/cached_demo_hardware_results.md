# Cached demo hardware results

Date: 2026-07-30

## Goal

Create a repository-level `cacheResults` folder for user-supplied,
successfully completed hardware results so demonstrations can retain known
examples for Hybrid, FRQI, and Grover modes.

## Branch

- `feature/real-hardware-routing`

## Decisions

- Store one normalized JSON document per hardware result under an
  algorithm-specific subfolder.
- Maintain `cacheResults/index.json` as the machine-readable catalog.
- Record only supplied values and directly verifiable derivatives, such as the
  sum of measurement counts.
- Mark the provenance as `user_provided`.
- Do not place credentials or provider tokens in cached results.
- Do not automatically substitute cached data for a live hardware call in
  this task. Runtime replay requires an explicit UI/API cache-selection policy
  so a cached result cannot be mistaken for a newly completed QPU job.

## Verification

- Parse all added JSON files.
- Confirm measurement counts sum to the reported 1,024 shots.
- Run `git diff --check`.

## Implementation log

- Created `cacheResults/{hybrid,frqi,grover}`.
- Added a machine-readable cache catalog.
- Stored the supplied Hybrid result from `ibm_marrakesh` under its remote IBM
  job ID.
- JSON parsing passed.
- The eight measurement counts sum to 1,024, matching `returnedShots`.
- `git diff --check` passed.
