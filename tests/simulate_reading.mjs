import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Story } from "../js/story.js";

// This loads the exact exported performance data used by the website.
const storyData = JSON.parse(readFileSync(new URL("../data/story.json", import.meta.url), "utf8"));

// This returns a fresh story without browser-only rendering callbacks.
function makeStory() {
  let finished = 0;
  const story = new Story(storyData.lines, { onFinish: () => { finished += 1; } });
  return { story, getFinished: () => finished };
}

// This reads all lines cleanly one word at a time and checks the story ends in order.
function testCleanReading() {
  const { story, getFinished } = makeStory();

  for (const line of storyData.lines) {
    for (const word of line.text.split(/\s+/)) {
      story.processTranscript(word, false);
    }
  }

  assert.equal(story.finished, true);
  assert.equal(story.previousLine, "Right here.");
  assert.equal(getFinished(), 1);
}

// This checks that remaining tokens can light and complete the next line in one result.
function testRunTogether() {
  const { story } = makeStory();
  story.processTranscript(`${storyData.lines[0].text} ${storyData.lines[1].text}`, true);
  assert.equal(story.activeLine, 2);
  assert.equal(story.previousLine, storyData.lines[1].text);
}

// This checks that a final result for a skipped line advances through findBestCue.
function testSkippedLineRecovery() {
  const { story } = makeStory();
  story.processTranscript(storyData.lines[2].text, true);
  assert.equal(story.activeLine, 3);
  assert.equal(story.previousLine, storyData.lines[2].text);
  assert.ok(story.lastBestScore >= 0.34);
}

// This checks common speech errors, missing words, and close endings without a microphone.
function testNoisyReading() {
  const { story } = makeStory();
  story.activeLine = 2;
  story.processTranscript("the window face west and in the afternoons everything went cold", true);
  assert.equal(story.activeLine, 3);
}

// This checks the two number conversions required for browser word alignment.
function testNumberReading() {
  const first = makeStory().story;
  first.activeLine = 8;
  first.processTranscript("The summer I turned 17 we moved", true);
  assert.equal(first.activeLine, 9);

  const second = makeStory().story;
  second.activeLine = 25;
  second.processTranscript("For months after I woke at 3 in the morning", true);
  assert.equal(second.activeLine, 26);
}

// This runs all simulated readings and reports a single useful result for CI or hand checks.
function run() {
  testCleanReading();
  testRunTogether();
  testSkippedLineRecovery();
  testNoisyReading();
  testNumberReading();
  console.log("simulate_reading.mjs passed clean, joined, skipped, noisy, and number readings");
}

run();
