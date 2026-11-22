# Feature Specification: SIR-Based Laptop Selection Service

**Feature Branch**: `001-sir-laptop-selection`

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Разработка веб-сервиса, помогающего пользователям выбрать оптимальную модель ноутбука (или ПК) на основе их бюджета, сферы деятельности и личных предпочтений, используя метод SIR для многокритериальной оценки доступных моделей."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a personalized ranking without an account (Priority: P1)

A shopper who needs a laptop for study and software development opens the service, states
a maximum budget, picks the intended uses, and rates how much each characteristic matters
(price, performance, memory, weight, battery life, screen, warranty). In one step the
service returns the available models that fit the budget, ordered from best to worst fit,
each with a short explanation of why it placed where it did.

**Why this priority**: This is the product. Everything else (accounts, saved profiles,
comparison views) only improves the experience of a ranking that must already exist and be
trustworthy. Delivering only this story yields a usable, demonstrable service.

**Independent Test**: With a pre-loaded catalog and no registered account, a tester enters
budget, usage goals, and weights, then receives an ordered list of in-budget models. The
test passes when the order changes predictably when weights change and every displayed
model has a visible rationale.

**Acceptance Scenarios**:

1. **Given** a catalog of models and a shopper with an 80,000 RUB budget who studies and
   programs, **When** the shopper submits these preferences with default weights, **Then**
   the service returns only models priced at or below 80,000 RUB, ordered by their SIR
   multi-criteria score, each with a one-line reason for its position.
2. **Given** the same shopper and catalog, **When** the shopper raises the importance of
   battery life, **Then** models with longer battery life move up the list relative to
   models that are otherwise equal, and the change is visible in the explanations.
3. **Given** any completed ranking, **When** the shopper repeats the identical preference
   set, **Then** the resulting order is identical, including the ordering of tied models.

---

### User Story 2 - Save a profile and criterion weights (Priority: P2)

A shopper creates a personal profile containing usage goals, budget, preferred brand,
preferred operating system, preferred form factor, and the importance of each of the seven
criteria. The profile can be edited later, and the saved weights are reused the next time
the shopper asks for recommendations.

**Why this priority**: Repeated shoppers should not re-enter preferences on every visit, and
the coursework requires profile management. It depends on the ranking from Story 1 but does
not change how ranking works.

**Independent Test**: A tester registers, saves a profile with a non-default weight set,
signs out, signs back in, and confirms that the stored weights are applied to a new ranking
without re-entry.

**Acceptance Scenarios**:

1. **Given** a new visitor, **When** they create an account and save a profile with weights
   of 20% price, 20% performance, 15% memory, 10% weight, 20% battery, 10% screen, and 5%
   warranty, **Then** the profile is stored and confirmed as saved.
2. **Given** a saved profile, **When** the shopper changes a single weight and saves, **Then**
   only that weight changes, the total remains 100%, and the next ranking reflects the new
   weight.
3. **Given** a shopper who has saved preferences, **When** they request recommendations
   without re-entering them, **Then** the saved preferences are applied and displayed as the
   active settings.

---

### User Story 3 - Compare and filter candidate models (Priority: P3)

A shopper who has a shortlist puts two to four models side by side and sees their values for
all seven criteria in one table, with the best value in each row highlighted. Filters narrow
the list by brand, operating system, form factor, and budget.

**Why this priority**: Decisions between near-equal models drive satisfaction, and comparison
is required by the coursework, but the service is already useful without it.

**Independent Test**: From any ranking, a tester selects three models and receives a
comparison table covering all seven criteria with per-row best values marked; applying a
brand filter removes non-matching models from the list.

**Acceptance Scenarios**:

1. **Given** a ranking containing at least four models, **When** the shopper selects two to
   four of them, **Then** a side-by-side table shows all seven criteria per model and
   highlights the best value in every row.
2. **Given** the same ranking, **When** the shopper filters by one brand and one operating
   system, **Then** only models matching both filters remain, and the ordering of the
   remaining models is preserved.
3. **Given** filters that exclude every model, **When** the filter is applied, **Then** the
   service explains that nothing matches and suggests which filter to relax, without showing
   an error page.

---

### User Story 4 - Understand why a model ranked where it did (Priority: P4)

A shopper opens the details of any ranked model and sees, per criterion, its normalized
value and how much that criterion contributed to its overall position, including the
criteria that pulled it down.

**Why this priority**: A recommendation service is only credible if it can justify results;
the coursework also grades method transparency. It refines Story 1 and can be demonstrated
on a single ranking.

**Independent Test**: A tester opens the details of the second-ranked model and can state,
using the displayed per-criterion contributions, which two criteria helped it most and which
one hurt it most.

**Acceptance Scenarios**:

1. **Given** any ranked result, **When** the shopper opens a model's details, **Then** the
   service shows its normalized value for each of the seven criteria and each criterion's
   contribution to the model's score.
2. **Given** a model's detail view, **When** the shopper asks how it compares with the
   top-ranked model, **Then** the service shows the score gap and the criteria responsible
   for that gap.

---

### Edge Cases

- **No model fits the budget or filters**: the service returns an empty state with the
  closest budget threshold and suggests which constraint to relax; it never shows a ranking
  error.
- **Only one eligible model**: the service ranks a single model and explains that no
  alternative matched, rather than hiding the result.
- **All eligible models share the same value for a criterion**: that criterion contributes
  nothing to the differences, and the ranking still produces a defined, stable order.
- **A model cannot be published without values for all seven criteria**: the admin
  endpoint rejects it with `422` and the schema is `NOT NULL` on every criterion, so a
  ranked model always has complete data. There is no "excluded for missing data" state.
- **Weights are zero, negative, or do not total 100%**: the service rejects the input before
  ranking and states what must be fixed.
- **A shopper changes preferences after viewing results**: the displayed ranking is
  recomputed from the new inputs; stale results are never shown as current.
- **Two models share a name or the catalog repeats a record**: each model keeps a stable
  identity, and ties are broken by that identity so repeated requests return the same order.
- **Catalog has thousands of models**: the shopper still sees a result promptly and can
  narrow it with filters.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST let a user state a maximum budget, one or more intended uses
  (study/office, software development, design or video editing, gaming), an optional brand
  preference, an optional operating-system preference, and a preferred form factor.
- **FR-002**: The service MUST let a user express the importance of each of the seven
  criteria: price (lower is better), processor performance (higher is better), memory
  (higher is better), weight (lower is better), battery life (higher is better), screen
  quality (higher is better), and warranty (higher is better).
- **FR-003**: The service MUST validate criterion weights as non-negative, with at least one
  weight above zero, and a total of 100% within a 0.5% tolerance, and MUST reject invalid
  input with a message naming the problem.
- **FR-004**: The service MUST rank eligible models with the SIR (Superiority and Inferiority
  Ranking) multi-criteria method: normalize each criterion to a common scale respecting its
  direction, compare every pair of models to derive superiority and inferiority indices,
  aggregate these into a single outranking score per model, and order models by that score.
- **FR-005**: The service MUST treat the budget as a hard constraint: models priced above the
  stated budget never appear in the ranking.
- **FR-006**: The service MUST present each ranked model with its position, its score, and a
  short user-readable reason for that position.
- **FR-007**: The service MUST show, for every ranked model, its normalized value and its
  contribution for each of the seven criteria.
- **FR-008**: The service MUST apply a deterministic, documented tie-break so that identical
  inputs always yield an identical order.
- **FR-009**: The service MUST let users filter a ranking by brand, operating system, form
  factor, and budget, and MUST preserve the SIR order among the remaining models.
- **FR-010**: The service MUST let users place two to four models in a side-by-side
  comparison covering all seven criteria and highlight the best value per criterion.
- **FR-011**: The service MUST let users create an account, sign in, and sign out, and MUST
  ensure that a user can view and change only their own profile.
- **FR-012**: The service MUST persist each saved profile with its criterion weights and MUST
  reuse those weights for subsequent rankings of that user.
- **FR-013**: The service MUST let users change individual profile values and weights without
  re-entering the whole profile.
- **FR-014**: The service MUST let users browse the full catalog of models with all seven
  criteria and their prices, independently of any ranking.
- **FR-015**: The service MUST let a catalog maintainer add, update, and retire models,
  requiring a value for every criterion before a model becomes eligible for ranking.
- **FR-016**: The service MUST record the catalog state and the preference set used for each
  ranking it presents, so that a displayed result can be reproduced later.
- **FR-017**: The service MUST display all user-facing text, criteria, and units in Russian,
  and prices in Russian rubles.
- **FR-018**: The service MUST present results on both desktop and mobile screens without
  loss of content or ordering.

### Key Entities *(include if feature involves data)*

- **Shopper Profile**: A person's stated needs and preferences: intended uses, maximum
  budget, brand preference, operating-system preference, form factor, and the seven
  criterion weights. Belongs to exactly one account when saved; may exist unsaved for a
  single guest session.
- **Criterion**: One of the seven decision dimensions, with its human-readable name, its
  direction (minimize or maximize), its unit, and its meaning for comparison. Fixed for this
  release at seven.
- **Device Model**: A laptop offered in the catalog, with brand, model name, operating system,
  form factor, price, and a value for each of the seven criteria. A model without a complete
  criterion set cannot be ranked.
- **Ranking Request**: The exact preference set, catalog snapshot, and timestamp used to
  produce a result. Used to reproduce a ranking.
- **Ranking Result**: The ordered models with their SIR scores, per-criterion normalized
  values, per-criterion contributions, and the tie-break applied.
- **Comparison Set**: A user-selected group of two to four models drawn from one ranking for
  side-by-side viewing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor can go from opening the service to a ranked shortlist in
  under 2 minutes, using no more than 10 inputs.
- **SC-002**: In a usability check with at least 5 representative shoppers, every participant
  can name at least one model they would consider from the top three results without outside
  help.
- **SC-003**: In the same check, at least 4 of 5 participants can explain, from the displayed
  per-criterion contributions, why the top model beat the runner-up.
- **SC-004**: Results for a catalog of up to 5,000 models appear within 3 seconds of
  submitting preferences on a typical laptop and a typical smartphone.
- **SC-005**: At least 90% of first-time participants complete profile creation and a first
  ranking without assistance.
- **SC-006**: 100% of the edge cases listed above return a deliberate, explainable outcome
  rather than an error or a blank screen, as verified by the acceptance test set.
- **SC-007**: Repeating an identical request against an unchanged catalog produces an
  identical ordered list 100% of the time, including tie ordering.
- **SC-008**: A displayed ranking can be reproduced on demand from its recorded catalog
  snapshot and preference set, with no more than a 0.01 difference in reported scores.

## Assumptions

- **Scope of devices**: this release covers laptops. Desktop PCs are out of scope because
  two criteria (weight and battery life) do not apply to them; extending the criteria set is
  a separate feature. The catalog may later include desktops without changing the ranking
  approach.
- **Single market and currency**: prices are in Russian rubles, include tax, and refer to one
  retail market. Currency conversion, regional pricing, and live price feeds are out of
  scope.
- **Catalog source**: a maintainer refreshes the catalog from a configured live source
  (JSON feed or an HTML page they are permitted to read) or a CSV export; the service does
  not scrape retailer sites by default, records the source and fetch time per model, and
  degrades to the last good data rather than emptying the catalog. Catalog size is expected
  to stay below 5,000 models.
- **No transaction handling**: the service recommends devices and links to details; it does
  not sell, reserve, or process payments.
- **Guest use**: a visitor can obtain a ranking without an account. Accounts exist to save
  profiles and weights.
- **Soft preferences are display-only**: brand, operating-system, and form-factor
  preferences are recorded with a ranking request and stored for future filtering, but they
  do not affect eligibility or the SIR score in this release. Hard filtering is available
  on the catalog and on stored rankings. This is stated in the interface so a shopper is
  never misled into thinking an ignored preference changed the result.
- **Language**: the interface is Russian-only for this release; the rubric, units, and
  criteria names are Russian.
- **Data minimization**: only preferences and account identifiers are stored; no payment or
  identity documents are collected.
- **Availability**: users have a working internet connection; offline use is out of scope.
- **Catalog values**: price, performance, memory, weight, battery life, screen quality, and
  warranty are recorded once per model and are assumed correct as entered; the service flags
  but does not correct missing data.
- **Out of scope for this feature**: price-drop alerts, user reviews, retailer integration,
  multi-language interface, and desktop-PC criteria.
