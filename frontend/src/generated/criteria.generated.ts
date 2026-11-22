// GENERATED from shared/criteria.json by criteria.codegen.mjs. Do not edit.
export type CriterionKey = "price" | "performance" | "memory" | "weight" | "battery" | "screen" | "warranty";
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

export const CRITERIA_VERSION = "1.0.0";

export const CRITERIA: readonly Criterion[] = [
  {
    "key": "price",
    "order": 1,
    "label_ru": "Цена",
    "direction": "min",
    "unit": "RUB",
    "storage_field": "price_minor",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  },
  {
    "key": "performance",
    "order": 2,
    "label_ru": "Производительность процессора",
    "direction": "max",
    "unit": "points",
    "storage_field": "cpu_score",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  },
  {
    "key": "memory",
    "order": 3,
    "label_ru": "Объём оперативной памяти",
    "direction": "max",
    "unit": "GB",
    "storage_field": "ram_gb",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  },
  {
    "key": "weight",
    "order": 4,
    "label_ru": "Вес",
    "direction": "min",
    "unit": "g",
    "storage_field": "weight_g",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  },
  {
    "key": "battery",
    "order": 5,
    "label_ru": "Время автономной работы",
    "direction": "max",
    "unit": "minutes",
    "storage_field": "battery_minutes",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  },
  {
    "key": "screen",
    "order": 6,
    "label_ru": "Качество экрана",
    "direction": "max",
    "unit": "score_0_10",
    "storage_field": "screen_score",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 1
  },
  {
    "key": "warranty",
    "order": 7,
    "label_ru": "Гарантия",
    "direction": "max",
    "unit": "months",
    "storage_field": "warranty_months",
    "indifference_threshold": 0,
    "preference_threshold": 1,
    "display_decimals": 0
  }
];

export const CRITERION_KEYS: readonly CriterionKey[] = CRITERIA.map((c) => c.key);

export const VOCABULARIES = {
  "goals": [
    "study",
    "development",
    "design",
    "gaming"
  ],
  "os": [
    "windows",
    "macos",
    "linux"
  ],
  "form_factor": [
    "ultrabook",
    "laptop",
    "gaming",
    "convertible"
  ]
} as const;
