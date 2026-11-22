# ADR 0003: Catalog data comes from a source chain, not a hard-coded shop

**Status**: accepted (2026-11-22)

## Context

The catalog needs realistic, current prices. Two forces conflict: the spec keeps
retailer scraping out of scope and gives catalog maintenance to a maintainer, while
the demo needs data that is not frozen at build time.

## Decision

Resolve the catalog through an ordered chain, stopping at the first source that yields
valid rows:

1. a live JSON feed (`CATALOG_LIVE_URL` + field mapping),
2. a CSS-selector config for an HTML page the operator may read (`CATALOG_HTML_CONFIG`),
3. a CSV export (`CATALOG_CSV_PATH`),
4. the bundled snapshot.

Every row records `source` and `fetched_at`; `/models` exposes them as `meta` and the
catalog page renders them. A failed refresh leaves the existing catalog untouched and
returns `503 catalog_unavailable`. Guest rankings are addressable by their unguessable
id so a visitor can replay and compare the result they were shown.

## Why not scrape a specific retailer

DNS answers `401`, M.Video `403`, and Citilink fails certificate validation from the
development network; those sites also forbid automated access in their terms. Hard-coding
one shop would ship a fragile, possibly unlawful integration. Configuration lets the
operator point at an API or feed they are entitled to use, with CSV as the offline path.
