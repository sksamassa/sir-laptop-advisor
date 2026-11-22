# Glossary: one term per concept, Russian and English.
# Backend, database, API, and UI must use these names consistently
# (constitution, Principle III).

| Русский | English | Meaning in this project |
|---------|---------|-------------------------|
| Альтернатива | Alternative | A laptop model that can be ranked. Stored in `device_models`. |
| Критерий | Criterion | One of the seven decision dimensions (price, performance, memory, weight, battery, screen, warranty). Defined once in `shared/criteria.json`. |
| Вес критерия | Criterion weight | Non-negative importance of a criterion; the seven weights sum to 1. Stored on `profiles`. |
| Допустимое множество | Eligible set | Active models whose price is at or below the stated budget; the pool that is normalized and ranked. |
| Нормализация | Normalization | Min-max mapping of a criterion to `[0, 1]` with direction applied, computed over the eligible set. |
| Индекс превосходства | Superiority index | `pi+(a, b)`: weighted preference of alternative `a` over `b`, summed across criteria. |
| Индекс неполноценности | Inferiority index | `pi-(a, b) = pi+(b, a)`. |
| Поток превосходства | Superiority flow | `Phi+(a)`: sum of `pi+(a, b)` over all other alternatives. |
| Поток неполноценности | Inferiority flow | `Phi-(a)`: sum of `pi+(b, a)` over all other alternatives. |
| Чистый поток | Net flow / SIR score | `Phi+(a) - Phi-(a)`; alternatives are ordered by it descending. |
| Порог безразличия | Indifference threshold | `q`: normalized difference at or below which two values are treated as equal. |
| Порог предпочтения | Preference threshold | `p`: normalized difference at or above which one value is strictly preferred. Must exceed `q`. |
| Ранжирование | Ranking | A stored, replayable ordering of alternatives with scores, contributions, and reasons. |
| Настройки профиля | Shopper profile | Budget, goals, soft preferences, and weights saved by an account. |
| Мягкое предпочтение | Soft preference | A stated brand, OS, or form-factor preference recorded with a request; it does not filter the eligible set. |
| Администратор каталога | Catalog maintainer | Account with `role = 'maintainer'` allowed to add, update, retire, and republish models. |
| Снимок ранжирования | Ranking snapshot | The preferences and eligible models stored with a ranking so it can be reproduced exactly. |
| Версия алгоритма | Algorithm version | Identifier (e.g. `sir-1.0.0`) stored with each ranking. |
