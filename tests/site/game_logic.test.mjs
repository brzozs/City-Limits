import test from "node:test";
import assert from "node:assert/strict";

import {
  CAR_SPEED,
  CITY_DIFFICULTY,
  TOOL_ORDER,
  calculateFlowRate,
  createSpentTools,
  getArms,
  getSpawnInterval,
  isToolSpent,
  spendTool,
} from "../../site/game-logic.mjs";

test("mobile demo keeps Python car speed parity", () => {
  assert.equal(CAR_SPEED, 80);
});

test("mobile demo keeps Python city difficulty parity", () => {
  assert.deepEqual(CITY_DIFFICULTY, {
    "New York City": 1.0,
    "Los Angeles": 0.85,
    "Chicago": 1.2,
  });
});

test("mobile demo keeps Python palette order parity", () => {
  assert.deepEqual(TOOL_ORDER, [
    "T_INTERSECTION",
    "TRUMPET",
    "Y_INTERSECTION",
    "FOUR_WAY",
    "ROUNDABOUT",
    "CLOVERLEAF",
    "DIAMOND",
    "PARTIAL_CLOVERLEAF",
  ]);
});

test("three-arm tools rotate like the Python version", () => {
  assert.deepEqual(getArms({ type: "T_INTERSECTION", rotation: 0 }), ["N", "E", "W"]);
  assert.deepEqual(getArms({ type: "T_INTERSECTION", rotation: 1 }), ["N", "S", "E"]);
  assert.deepEqual(getArms({ type: "TRUMPET", rotation: 2 }), ["S", "E", "W"]);
  assert.deepEqual(getArms({ type: "PARTIAL_CLOVERLEAF", rotation: 3 }), ["N", "S", "W"]);
});

test("flow rate keeps routing penalty parity", () => {
  const stats = [[80, 1, 0]];
  const full = calculateFlowRate(stats, 1, 1);
  const half = calculateFlowRate(stats, 2, 1);

  assert.equal(full, 1);
  assert.equal(half, 0.5);
});

test("Los Angeles stays harder than New York and Chicago at the same moment", () => {
  const rushHour = (75 * 17) / 24;
  const losAngeles = getSpawnInterval("Los Angeles", rushHour, 1);
  const newYork = getSpawnInterval("New York City", rushHour, 1);
  const chicago = getSpawnInterval("Chicago", rushHour, 1);

  assert.ok(losAngeles < newYork);
  assert.ok(newYork < chicago);
});

test("tool inventory is consumable per run like the Python palette", () => {
  const spent = createSpentTools();

  assert.equal(isToolSpent(spent, "ROUNDABOUT"), false);

  const nextSpent = spendTool(spent, "ROUNDABOUT");
  assert.equal(isToolSpent(nextSpent, "ROUNDABOUT"), true);
  assert.equal(isToolSpent(nextSpent, "FOUR_WAY"), false);
});
