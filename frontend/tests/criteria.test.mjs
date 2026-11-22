// Guards the generated criteria module against drift from shared/criteria.json.
// Runs with the built-in test runner: node --test tests/

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const registry = JSON.parse(readFileSync(join(root, "..", "shared", "criteria.json"), "utf8"));
const generated = readFileSync(join(root, "src", "generated", "criteria.generated.ts"), "utf8");

test("generated criteria match the registry", () => {
  assert.match(generated, new RegExp(`CRITERIA_VERSION = "${registry.version}"`));
  for (const criterion of registry.criteria) {
    assert.ok(generated.includes(`"key": "${criterion.key}"`), `missing ${criterion.key}`);
    assert.ok(generated.includes(criterion.label_ru), `missing label ${criterion.label_ru}`);
    assert.ok(
      generated.includes(`"direction": "${criterion.direction}"`),
      `missing direction for ${criterion.key}`,
    );
  }
});

test("registry keeps exactly seven unique criteria in order", () => {
  assert.equal(registry.criteria.length, 7);
  const orders = registry.criteria.map((criterion) => criterion.order).sort((a, b) => a - b);
  assert.deepEqual(orders, [1, 2, 3, 4, 5, 6, 7]);
  const keys = new Set(registry.criteria.map((criterion) => criterion.key));
  assert.equal(keys.size, 7);
});

test("every criterion declares a valid threshold pair", () => {
  for (const criterion of registry.criteria) {
    assert.ok(criterion.indifference_threshold >= 0);
    assert.ok(criterion.indifference_threshold < criterion.preference_threshold);
    assert.ok(criterion.preference_threshold <= 1);
  }
});
