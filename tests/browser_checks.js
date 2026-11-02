// This runs in playwright-cli against a local server to check browser failure states.
async (page) => {
  const base = "http://127.0.0.1:8000/";
  const browserMessage = "This browser can't listen. Please open this page in Chrome, Edge or Safari.";
  const microphoneMessage = "Microphone access is needed. Allow it in your browser settings and reload the page.";

  // This checks one simulated browser or recognition failure from the start screen.
  async function checkFailure(name, setup, expected) {
    const context = await page.context().browser().newContext();
    const testPage = await context.newPage();
    await testPage.addInitScript(setup);
    await testPage.goto(base);
    await testPage.locator("#title-screen").click();
    await testPage.locator("#begin-screen").click();
    try {
      await testPage.waitForFunction((message) => document.querySelector("#status-line").textContent === message, expected, { timeout: 6000 });
    } catch (error) {
      const actual = await testPage.locator("#status-line").textContent();
      throw new Error(`${name}: expected ${expected}, got ${actual}`);
    }
    await testPage.waitForTimeout(500);
    const current = await testPage.locator("#current-line").textContent();
    if (current.trim()) throw new Error(`${name}: story text remained visible`);
    await context.close();
    return `${name}: passed`;
  }

  const results = [];
  results.push(await checkFailure("Brave", () => {
    Object.defineProperty(navigator, "brave", { value: {}, configurable: true });
  }, browserMessage));
  results.push(await checkFailure("Opera", () => {
    Object.defineProperty(navigator, "userAgent", { value: "Test OPR/114.0", configurable: true });
  }, browserMessage));
  results.push(await checkFailure("No recognition start", () => {
    const MockRecognition = class {
      start() {}
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  }, browserMessage));
  results.push(await checkFailure("Network before start", () => {
    const MockRecognition = class {
      start() { this.onerror({ error: "network" }); }
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  }, browserMessage));
  results.push(await checkFailure("Permission denied", () => {
    const MockRecognition = class {
      start() { this.onerror({ error: "not-allowed" }); }
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  }, microphoneMessage));
  results.push(await checkFailure("Delayed permission denial", () => {
    const MockRecognition = class {
      start() { setTimeout(() => this.onerror({ error: "not-allowed" }), 0); }
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  }, microphoneMessage));

  // This uses a working mock recognizer to keep the performance screen visible.
  const layoutContext = await page.context().browser().newContext();
  const layoutPage = await layoutContext.newPage();
  await layoutPage.addInitScript(() => {
    const MockRecognition = class {
      start() { this.onstart?.(); }
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  });
  await layoutPage.goto(base);
  await layoutPage.locator("#title-screen").click();
  await layoutPage.locator("#begin-screen").click();
  await layoutPage.locator("#music-values").waitFor({ state: "visible" });
  const overlaps = (first, second) => first.left < second.right && first.right > second.left
    && first.top < second.bottom && first.bottom > second.top;

  // This checks that music values are visible and separate from content at each width.
  for (const [width, height] of [[1280, 720], [1440, 900], [1920, 1080], [680, 900]]) {
    await layoutPage.setViewportSize({ width, height });
    const boxes = await layoutPage.evaluate(() => {
    const rect = (selector) => document.querySelector(selector).getBoundingClientRect().toJSON();
      return {
        values: rect("#music-values"), image: rect("#image-box"), story: rect(".story-column"),
        scrollWidth: document.documentElement.scrollWidth,
      };
    });
    if (!boxes.values.width || overlaps(boxes.values, boxes.image) || overlaps(boxes.values, boxes.story)) {
      throw new Error(`Music values overlap the image or story at ${width} by ${height}`);
    }
    if (boxes.scrollWidth > width) {
      throw new Error(`Horizontal overflow at ${width} by ${height}`);
    }
  }
  results.push("Music values layout at four sizes: passed");
  await layoutContext.close();
  return results;
}
