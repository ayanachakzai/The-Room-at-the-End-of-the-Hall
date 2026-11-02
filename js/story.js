import { alignmentToken, alignmentTokens, findBestCue, wordsMatch } from "./matcher.js";

// This lets the site compare live-like first-word cues with line-complete cues.
export const CUE_TIMING = "first-word";

// This holds the reading position and lights words as each recognition result arrives.
export class Story {
  // This stores callbacks so the browser view and media stay separate from matching.
  constructor(lines, callbacks = {}) {
    this.lines = lines;
    this.activeLine = 0;
    this.spokenCount = 0;
    this.lineTokenOffset = 0;
    this.previousLine = "";
    this.lastBestScore = 0;
    this.callbacks = callbacks;
    this.finished = false;
  }

  // This returns display tokens while retaining the original punctuation in the view.
  activeTokens() {
    if (this.finished || !this.lines[this.activeLine]) {
      return [];
    }

    return this.lines[this.activeLine].text.split(/\s+/).map(alignmentToken);
  }

  // This provides the complete state the UI needs to render the current story line.
  state() {
    return {
      activeLine: this.activeLine,
      spokenCount: this.spokenCount,
      previousLine: this.previousLine,
      finished: this.finished,
      line: this.finished ? null : this.lines[this.activeLine],
      lastBestScore: this.lastBestScore,
    };
  }

  // This notifies the page whenever the active line or spoken-word count changes.
  emitView() {
    this.callbacks.onView?.(this.state());
  }

  // This applies a cue at the selected timing without applying one line twice.
  emitCue(line, timing) {
    if (CUE_TIMING === timing) {
      this.callbacks.onCue?.(line);
    }
  }

  // This starts rendering the first line after the initial media cue is already active.
  start() {
    this.emitView();
  }

  // This completes the current line and preserves the result offset for leftover words.
  completeLine(lastTokenIndex = -1) {
    if (this.finished || !this.lines[this.activeLine]) {
      return;
    }

    const completedLine = this.lines[this.activeLine];
    this.emitCue(completedLine, "line-complete");
    this.previousLine = completedLine.text;
    this.callbacks.onLineComplete?.(completedLine);
    this.activeLine += 1;
    this.spokenCount = 0;
    this.lineTokenOffset = lastTokenIndex + 1;

    if (this.activeLine >= this.lines.length) {
      this.finished = true;
      this.emitView();
      this.callbacks.onFinish?.();
      return;
    }

    this.emitView();
  }

  // This handles the words in one interim or final recognition result in sequence.
  processTranscript(text, isFinal = false) {
    if (this.finished) {
      return;
    }

    const heard = alignmentTokens(text);
    this.lineTokenOffset = 0;
    let tokenIndex = this.lineTokenOffset;
    let firstWordLit = false;

    while (tokenIndex < heard.length && !this.finished) {
      const expected = this.activeTokens();
      let matchIndex = -1;

      for (
        let expectedIndex = this.spokenCount;
        expectedIndex < Math.min(expected.length, this.spokenCount + 4);
        expectedIndex += 1
      ) {
        if (wordsMatch(heard[tokenIndex], expected[expectedIndex])) {
          matchIndex = expectedIndex;
          break;
        }
      }

      if (matchIndex >= 0) {
        const wasUnstarted = this.spokenCount === 0;
        this.spokenCount = Math.max(this.spokenCount, matchIndex + 1);

        if (wasUnstarted && !firstWordLit) {
          this.emitCue(this.lines[this.activeLine], "first-word");
          firstWordLit = true;
        }

        this.emitView();

        if (this.spokenCount >= expected.length) {
          this.completeLine(tokenIndex);
        }
      }

      tokenIndex += 1;
    }

    if (!this.finished && isFinal && this.spokenCount >= this.activeTokens().length * 0.6) {
      this.completeLine(tokenIndex - 1);
    }

    if (!this.finished && isFinal) {
      this.recoverSkippedLines(text);
    }
  }

  // This advances only forward when a final speech result strongly matches a later cue.
  recoverSkippedLines(finalText) {
    const match = findBestCue(finalText, this.activeLine, this.lines);
    this.lastBestScore = match.score;

    if (match.index <= this.activeLine || match.score < 0.34) {
      this.emitView();
      return;
    }

    for (let index = this.activeLine; index <= match.index; index += 1) {
      this.previousLine = this.lines[index].text;
      this.callbacks.onLineComplete?.(this.lines[index]);
    }

    this.activeLine = match.index + 1;
    this.spokenCount = 0;
    this.lineTokenOffset = 0;

    if (this.activeLine >= this.lines.length) {
      this.finished = true;
      this.emitView();
      this.callbacks.onFinish?.();
      return;
    }

    this.emitView();
  }

  // This lets debug mode advance one line without a microphone.
  completeForDebug() {
    this.spokenCount = this.activeTokens().length;
    this.completeLine();
  }
}
