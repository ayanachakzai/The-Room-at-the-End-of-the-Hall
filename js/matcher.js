// This normalises speech and script text exactly like the live Python matcher.
export function normalizeText(text) {
  return String(text)
    .toLowerCase()
    .replaceAll("17", "seventeen")
    .replaceAll("3 in the morning", "three in the morning")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// This builds the character lookup used by Python difflib's SequenceMatcher.
function makeB2j(second) {
  const positions = new Map();

  for (let index = 0; index < second.length; index += 1) {
    const character = second[index];
    const items = positions.get(character) || [];
    items.push(index);
    positions.set(character, items);
  }

  if (second.length >= 200) {
    const limit = 1 + Math.floor(second.length / 100);

    for (const [character, items] of positions) {
      if (items.length > limit) {
        positions.delete(character);
      }
    }
  }

  return positions;
}

// This ports difflib.SequenceMatcher.find_longest_match for character strings.
function findLongestMatch(first, second, b2j, alo, ahi, blo, bhi) {
  let bestI = alo;
  let bestJ = blo;
  let bestSize = 0;
  let previousLengths = new Map();

  for (let firstIndex = alo; firstIndex < ahi; firstIndex += 1) {
    const lengths = new Map();
    const positions = b2j.get(first[firstIndex]) || [];

    for (const secondIndex of positions) {
      if (secondIndex < blo) {
        continue;
      }
      if (secondIndex >= bhi) {
        break;
      }

      const size = (previousLengths.get(secondIndex - 1) || 0) + 1;
      lengths.set(secondIndex, size);

      if (size > bestSize) {
        bestI = firstIndex - size + 1;
        bestJ = secondIndex - size + 1;
        bestSize = size;
      }
    }

    previousLengths = lengths;
  }

  while (
    bestI > alo
    && bestJ > blo
    && first[bestI - 1] === second[bestJ - 1]
  ) {
    bestI -= 1;
    bestJ -= 1;
    bestSize += 1;
  }

  while (
    bestI + bestSize < ahi
    && bestJ + bestSize < bhi
    && first[bestI + bestSize] === second[bestJ + bestSize]
  ) {
    bestSize += 1;
  }

  return [bestI, bestJ, bestSize];
}

// This returns matching blocks with the same queue and merge behaviour as difflib.
function matchingBlocks(first, second) {
  const b2j = makeB2j(second);
  const queue = [[0, first.length, 0, second.length]];
  const blocks = [];

  while (queue.length) {
    const [alo, ahi, blo, bhi] = queue.pop();
    const [firstIndex, secondIndex, size] = findLongestMatch(
      first,
      second,
      b2j,
      alo,
      ahi,
      blo,
      bhi,
    );

    if (!size) {
      continue;
    }

    blocks.push([firstIndex, secondIndex, size]);

    if (alo < firstIndex && blo < secondIndex) {
      queue.push([alo, firstIndex, blo, secondIndex]);
    }

    if (firstIndex + size < ahi && secondIndex + size < bhi) {
      queue.push([firstIndex + size, ahi, secondIndex + size, bhi]);
    }
  }

  blocks.sort((left, right) => left[0] - right[0] || left[1] - right[1]);
  const merged = [];
  let previousFirst = 0;
  let previousSecond = 0;
  let previousSize = 0;

  for (const [firstIndex, secondIndex, size] of blocks) {
    if (
      previousSize
      && previousFirst + previousSize === firstIndex
      && previousSecond + previousSize === secondIndex
    ) {
      previousSize += size;
      continue;
    }

    if (previousSize) {
      merged.push([previousFirst, previousSecond, previousSize]);
    }

    previousFirst = firstIndex;
    previousSecond = secondIndex;
    previousSize = size;
  }

  if (previousSize) {
    merged.push([previousFirst, previousSecond, previousSize]);
  }

  merged.push([first.length, second.length, 0]);
  return merged;
}

// This returns the faithful difflib SequenceMatcher ratio, including autojunk.
export function sequenceMatcherRatio(first, second) {
  const totalLength = first.length + second.length;

  if (!totalLength) {
    return 1;
  }

  const matches = matchingBlocks(first, second).reduce(
    (total, block) => total + block[2],
    0,
  );
  return (2 * matches) / totalLength;
}

// This combines sequence similarity, word overlap, and containment like the show.
export function textSimilarity(first, second) {
  const normalFirst = normalizeText(first);
  const normalSecond = normalizeText(second);

  if (!normalFirst || !normalSecond) {
    return 0;
  }

  const sequence = sequenceMatcherRatio(normalFirst, normalSecond);
  const firstWords = new Set(normalFirst.split(" "));
  const secondWords = new Set(normalSecond.split(" "));
  const sharedWords = [...firstWords].filter((word) => secondWords.has(word)).length;
  const overlap = sharedWords / Math.max(1, Math.min(firstWords.size, secondWords.size));
  const contained = normalFirst.includes(normalSecond) || normalSecond.includes(normalFirst) ? 1 : 0;

  return Math.max(sequence * 0.65 + overlap * 0.35, contained * 0.85);
}

// This finds the best nearby cue or four-line span using the live constants.
export function findBestCue(heard, currentIndex, lines) {
  const lookBack = 3;
  const lookAhead = 10;
  const maxSpan = 4;
  const minimumScore = 0.34;
  const start = Math.max(0, currentIndex - lookBack);
  const end = Math.min(lines.length, currentIndex + lookAhead);
  let bestIndex = currentIndex;
  let bestScore = -1;
  let bestText = lines[currentIndex].text;

  for (let index = start; index < end; index += 1) {
    for (let spanLength = 1; spanLength <= maxSpan; spanLength += 1) {
      const lastIndex = Math.min(lines.length - 1, index + spanLength - 1);

      if (lastIndex >= end) {
        break;
      }

      const spanText = lines.slice(index, lastIndex + 1).map((line) => line.text).join(" ");
      let score = textSimilarity(heard, spanText);

      if (index >= currentIndex) {
        score += 0.03;
      }
      if (index < currentIndex) {
        score -= 0.02 * (currentIndex - index);
      }

      if (score > bestScore) {
        bestIndex = lastIndex;
        bestScore = score;
        bestText = spanText;
      }
    }
  }

  if (bestScore < minimumScore) {
    return {
      index: currentIndex,
      score: bestScore,
      text: lines[currentIndex].text,
    };
  }

  return {
    index: bestIndex,
    score: Math.max(0, Math.min(1, bestScore)),
    text: bestText,
  };
}

// This converts a display or heard word into the alignment token used by the story.
export function alignmentToken(word) {
  return String(word)
    .toLowerCase()
    .replace(/\b17\b/g, "seventeen")
    .replace(/\b3\b/g, "three")
    .replace(/[^a-z0-9]/g, "");
}

// This splits a current speech result into alignment tokens without empty values.
export function alignmentTokens(text) {
  return String(text)
    .split(/\s+/)
    .map(alignmentToken)
    .filter(Boolean);
}

// This calculates a simple character edit distance for close speech-recognition matches.
function levenshteinDistance(first, second) {
  let previous = Array.from({ length: second.length + 1 }, (_, index) => index);

  for (let firstIndex = 1; firstIndex <= first.length; firstIndex += 1) {
    const current = [firstIndex];

    for (let secondIndex = 1; secondIndex <= second.length; secondIndex += 1) {
      const cost = first[firstIndex - 1] === second[secondIndex - 1] ? 0 : 1;
      current[secondIndex] = Math.min(
        current[secondIndex - 1] + 1,
        previous[secondIndex] + 1,
        previous[secondIndex - 1] + cost,
      );
    }

    previous = current;
  }

  return previous[second.length];
}

// This accepts exact words and sufficiently close longer words from speech recognition.
export function wordsMatch(heard, expected) {
  if (heard === expected) {
    return true;
  }
  if (heard.length < 4 || expected.length < 4) {
    return false;
  }

  const longest = Math.max(heard.length, expected.length);
  return 1 - levenshteinDistance(heard, expected) / longest >= 0.7;
}
