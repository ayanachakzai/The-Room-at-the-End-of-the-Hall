import { execFileSync } from "node:child_process";
import assert from "node:assert/strict";
import { normalizeText, sequenceMatcherRatio, textSimilarity } from "../js/matcher.js";

// This reads Python's difflib scores so the browser port can be checked exactly.
function loadReferenceScores() {
  const output = execFileSync("python3", ["matcher_reference.py", "--json"], {
    cwd: new URL(".", import.meta.url),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

// This compares every JavaScript score with the corresponding Python reference score.
function run() {
  const scores = loadReferenceScores();

  for (const score of scores) {
    const ratio = sequenceMatcherRatio(normalizeText(score.first), normalizeText(score.second));
    const similarity = textSimilarity(score.first, score.second);
    assert.ok(Math.abs(ratio - score.ratio) <= 0.0001, `ratio mismatch: ${score.first}`);
    assert.ok(Math.abs(similarity - score.similarity) <= 0.0001, `similarity mismatch: ${score.first}`);
  }

  console.log(`matcher.test.mjs passed ${scores.length} Python parity pairs`);
}

run();
