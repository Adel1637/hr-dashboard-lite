# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Import on phones: the column-mapping screen no longer overflows the page (dropdowns were
  cut off on narrow screens). Regression test added.
- Import report: the line number shown is now the one displayed in Excel even when the file has
  blank rows (before the header or between data); it was shifted by the number of blank rows.
- Import report: row error messages follow the interface language (they were always French) and
  the counters no longer read "1 rows".
- CSV import: a one-column title above the header row no longer makes the file unreadable.
- Sign-in page: white text on a darkened accent, readable in both themes and with any accent
  colour (WCAG AA contrast checked by a test).

## [0.1.0] — 2026-11-02

First public release of the Lite edition.

- Excel and CSV import with header, separator and encoding detection
- Column-mapping assistant with automatic suggestions and per-format memory
- Row-level validation report with Excel line numbers
- Headcount module with global filters (reference date, period, site, department, category,
  contract, sex)
- Data table with server-side search, sorting and pagination
- Single admin account, scrypt password hashing, JWT sessions, login rate limiting, strict CSP
- Light and dark themes, French and English, bundled Plus Jakarta Sans font (works offline)
- Fictional data generator (50, 1,000 and 20,000 employees)
- Docker image, GitHub Actions CI, pytest suite
