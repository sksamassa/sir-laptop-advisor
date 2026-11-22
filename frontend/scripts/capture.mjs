// Drives headless Edge over the DevTools protocol to verify the interactive flow
// and capture screenshots. Not part of the app; used for UI verification.
//
//   node scripts/capture.mjs <outDir> <wsUrl>

import { writeFileSync } from "node:fs";

const [outDir, wsUrl] = process.argv.slice(2);
if (!outDir || !wsUrl) {
  console.error("usage: node scripts/capture.mjs <outDir> <wsUrl>");
  process.exit(1);
}

const ws = new WebSocket(wsUrl);
let nextId = 0;
const pending = new Map();

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(JSON.stringify(message.error)));
  else resolve(message.result);
});

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function evaluate(expression) {
  const result = await send("Runtime.evaluate", { expression, returnByValue: true });
  return result.result?.value;
}

async function shot(name) {
  const capture = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${outDir}/${name}.png`, Buffer.from(capture.data, "base64"));
  console.log(`saved ${name}.png`);
}

await new Promise((resolve) => ws.addEventListener("open", resolve));
await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 1440,
  height: 1100,
  deviceScaleFactor: 1,
  mobile: false,
});

await send("Page.navigate", { url: "http://127.0.0.1:3000/" });
await wait(5000);
await shot("01-form");

const clickedSubmit = await evaluate(`
  (() => {
    const button = [...document.querySelectorAll("button")].find((node) =>
      node.textContent.includes("Подобрать ноутбук"),
    );
    if (!button) return false;
    button.click();
    return true;
  })()
`);
console.log("submit clicked:", clickedSubmit);
await wait(6000);
await shot("02-results");

const openedDetails = await evaluate(`
  (() => {
    const button = [...document.querySelectorAll("button")].find(
      (node) => node.textContent.trim() === "Почему так?",
    );
    if (!button) return false;
    button.click();
    return true;
  })()
`);
console.log("details opened:", openedDetails);
await wait(1500);
await shot("03-details");

const selected = await evaluate(`
  (() => {
    const chips = [...document.querySelectorAll("li button")].filter(
      (node) => node.textContent.trim() === "Сравнить",
    );
    return chips.length;
  })()
`);
console.log("compare chips available:", selected);
for (let index = 0; index < 3; index += 1) {
  await evaluate(`
    (() => {
      const chip = [...document.querySelectorAll("li button")].find(
        (node) => node.textContent.trim() === "Сравнить",
      );
      if (!chip) return false;
      chip.click();
      return true;
    })()
  `);
  await wait(500);
}
await shot("04-selected");

const openedCompare = await evaluate(`
  (() => {
    const button = [...document.querySelectorAll("button")].find((node) =>
      node.textContent.trim() === "Сравнить 3",
    );
    if (!button) return false;
    button.click();
    return true;
  })()
`);
console.log("compare opened:", openedCompare);
await wait(3000);
await shot("05-compare");

await send("Emulation.setDeviceMetricsOverride", {
  width: 390,
  height: 900,
  deviceScaleFactor: 2,
  mobile: true,
});
await send("Page.navigate", { url: "http://127.0.0.1:3000/catalog" });
await wait(5000);
await shot("06-mobile-catalog");

await send("Emulation.setDeviceMetricsOverride", {
  width: 1440,
  height: 1100,
  deviceScaleFactor: 1,
  mobile: false,
});
await send("Page.navigate", { url: "http://127.0.0.1:3000/" });
await wait(5000);

const setBudget = async (rubles) => {
  await evaluate(`
    (() => {
      const input = document.querySelector('input[aria-label="Бюджет в рублях"]');
      if (!input) return false;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      ).set;
      setter.call(input, String(${rubles}));
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return true;
    })()
  `);
  await wait(400);
  await evaluate(`
    (() => {
      const button = [...document.querySelectorAll("button")].find((node) =>
        node.textContent.includes("Подобрать ноутбук"),
      );
      if (!button) return false;
      button.click();
      return true;
    })()
  `);
  await wait(4000);
};

await setBudget(30000);
await shot("07-budget-30000");

await setBudget(10000);
await shot("08-budget-10000");


ws.close();
process.exit(0);
