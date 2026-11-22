#!/usr/bin/env node
// Generates the frontend and backend representations of shared/criteria.json.
// The JSON file is the only authored definition; these outputs are derived.
//
// Usage: node shared/criteria.codegen.mjs [--check]
//   --check exits non-zero when a generated file is out of date.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, "shared", "criteria.json");
const tsTarget = join(root, "frontend", "src", "generated", "criteria.generated.ts");
const pyTarget = join(root, "backend", "src", "laptop_dss", "catalog", "domain", "criteria_generated.py");
// Packaged copy so the API can load the registry inside a container, where the
// repository's shared/ directory is not part of the image.
const jsonTarget = join(root, "backend", "src", "laptop_dss", "catalog", "domain", "criteria.json");
const check = process.argv.includes("--check");

const registry = JSON.parse(readFileSync(source, "utf8"));

const ts = `// GENERATED from shared/criteria.json by criteria.codegen.mjs. Do not edit.
export type CriterionKey = ${registry.criteria.map((c) => JSON.stringify(c.key)).join(" | ")};
export type CriterionDirection = "min" | "max";

export interface Criterion {
  readonly key: CriterionKey;
  readonly order: number;
  readonly label_ru: string;
  readonly direction: CriterionDirection;
  readonly unit: string;
  readonly storage_field: string;
  readonly indifference_threshold: number;
  readonly preference_threshold: number;
  readonly display_decimals: number;
}

export const CRITERIA_VERSION = ${JSON.stringify(registry.version)};

export const CRITERIA: readonly Criterion[] = ${JSON.stringify(registry.criteria, null, 2)};

export const CRITERION_KEYS: readonly CriterionKey[] = CRITERIA.map((c) => c.key);

export const VOCABULARIES = ${JSON.stringify(registry.vocabularies, null, 2)} as const;
`;

const py = `"""GENERATED from shared/criteria.json by criteria.codegen.mjs. Do not edit."""

from __future__ import annotations

CRITERIA_VERSION = "${registry.version}"

CRITERIA_DATA: tuple[dict[str, object], ...] = (
${registry.criteria.map((c) => "    " + JSON.stringify(c).replace(/true/g, "True").replace(/false/g, "False")).join(",\n")},
)

VOCABULARIES: dict[str, tuple[str, ...]] = {
${Object.entries(registry.vocabularies)
  .map(([k, v]) => `    "${k}": (${v.map((x) => JSON.stringify(x)).join(", ")},),`)
  .join("\n")}
}
`;

function emit(path, content) {
  if (check) {
    let current = "";
    try {
      current = readFileSync(path, "utf8");
    } catch {
      current = "";
    }
    if (current !== content) {
      console.error(`out of date: ${path}`);
      process.exitCode = 1;
    }
    return;
  }
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
  console.log(`wrote ${path}`);
}

emit(tsTarget, ts);
emit(pyTarget, py);
emit(jsonTarget, `${JSON.stringify(registry, null, 2)}\n`);
if (check && !process.exitCode) console.log("generated files are up to date");
