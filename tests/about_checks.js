// This runs in playwright-cli against a local server to check About navigation and layout.
async (page) => {
  const base = "http://127.0.0.1:8000/?debug=1";
  const assert = (condition, message) => {
    if (!condition) throw new Error(message);
  };
  const screen = async (id) => page.locator(id).evaluate((element) => element.classList.contains("is-visible"));

  await page.addInitScript(() => {
    window.testMicStarts = 0;
    const MockRecognition = class {
      start() { window.testMicStarts += 1; this.onstart?.(); }
      stop() {}
    };
    window.SpeechRecognition = MockRecognition;
    window.webkitSpeechRecognition = MockRecognition;
  });
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(base);
  await page.locator("#title-screen .about-toggle").click();
  assert(await screen("#about-screen"), "About did not open from the title screen");
  assert(await page.locator("#close-about").evaluate((element) => element === document.activeElement), "Close did not receive focus");
  await page.keyboard.press("Escape");
  assert(await screen("#title-screen"), "Escape did not return to the title screen");
  assert(await page.locator("#title-screen .about-toggle").evaluate((element) => element === document.activeElement), "Focus did not return to title About");

  await page.locator("#title-screen").click({ position: { x: 10, y: 10 } });
  assert(await screen("#begin-screen"), "The instruction screen did not open");
  const audioBefore = await page.evaluate(() => [Tone.getContext().state, Tone.Transport.state]);
  const beginAbout = page.locator("#begin-screen .about-toggle");
  await beginAbout.focus();
  await page.keyboard.press("Enter");
  assert(await screen("#about-screen"), "Keyboard About did not open from instructions");
  assert(await page.locator("#close-about").evaluate((element) => element === document.activeElement), "Close did not receive focus from instructions");
  const starts = await page.evaluate(() => [window.testMicStarts, Tone.getContext().state, Tone.Transport.state]);
  assert(starts[0] === 0 && starts[1] === audioBefore[0] && starts[2] === audioBefore[1], `About started microphone or music: ${starts}`);
  await page.locator("#close-about").click();
  assert(await screen("#begin-screen"), "Close did not return to instructions");
  assert(await beginAbout.evaluate((element) => element === document.activeElement), "Focus did not return to instruction About");
  await beginAbout.click();
  assert(await screen("#about-screen"), "Pointer About did not open from instructions");
  const pointerStarts = await page.evaluate(() => [window.testMicStarts, Tone.getContext().state, Tone.Transport.state]);
  assert(pointerStarts[0] === 0 && pointerStarts[1] === audioBefore[0] && pointerStarts[2] === audioBefore[1], `Pointer About started microphone or music: ${pointerStarts}`);
  await page.keyboard.press("Escape");
  assert(await screen("#begin-screen"), "Escape did not return to instructions");

  await page.locator("#begin-screen").click({ position: { x: 10, y: 10 } });
  assert(await screen("#performance-screen"), "The reading screen did not open");
  assert(await page.locator("#performance-screen .about-toggle").count() === 0, "About appeared during reading");
  await page.waitForFunction(() => Tone.Transport.state === "started", null, { timeout: 6000 });
  const started = await page.evaluate(() => window.testMicStarts);
  assert(started === 1, `The microphone start counter did not validate: ${started}`);
  for (let index = 0; index < 43; index += 1) await page.keyboard.press("ArrowRight");
  await page.waitForFunction(() => document.querySelector("#end-screen").classList.contains("is-visible"), null, { timeout: 15000 });
  await page.locator("#end-screen .about-toggle").click();
  assert(await screen("#about-screen"), "About did not open from the end screen");
  await page.locator("#close-about").click();
  assert(await screen("#end-screen"), "Close did not return to the end screen");
  assert(await page.locator("#end-screen .about-toggle").evaluate((element) => element === document.activeElement), "Focus did not return to end About");
  const afterEnd = await page.evaluate(() => [window.testMicStarts, Tone.Transport.state]);
  assert(afterEnd[0] === started && afterEnd[1] === "stopped", "Returning from About restarted the performance");

  for (const [width, height] of [[1280, 720], [390, 700]]) {
    await page.setViewportSize({ width, height });
    await page.locator("#end-screen .about-toggle").click();
    const layout = await page.evaluate(() => {
      const about = document.querySelector("#about-screen");
      const column = document.querySelector(".about-copy").getBoundingClientRect();
      const close = document.querySelector("#close-about").getBoundingClientRect();
      const heading = document.querySelector("#about-heading").getBoundingClientRect();
      return {
        scrollWidth: about.scrollWidth,
        clientWidth: about.clientWidth,
        scrollHeight: about.scrollHeight,
        clientHeight: about.clientHeight,
        columnWidth: column.width,
        closeRight: close.right,
        closeBottom: close.bottom,
        headingTop: heading.top,
      };
    });
    assert(layout.scrollWidth <= layout.clientWidth, `Horizontal overflow at ${width}`);
    assert(layout.scrollHeight > layout.clientHeight, `About did not scroll at ${width}`);
    assert(layout.columnWidth <= 608, `Column exceeded 38rem at ${width}`);
    assert(layout.closeRight <= width && layout.closeBottom < layout.headingTop, `Close overlapped content at ${width}`);
    await page.locator("#close-about").click();
  }

  await page.emulateMedia({ reducedMotion: "reduce" });
  const transition = await page.locator("#about-screen").evaluate((element) => getComputedStyle(element).transitionDuration);
  assert(transition === "0.001s", `Reduced motion fade was ${transition}`);
  return "About navigation, activation, focus, end state, layouts and reduced motion: passed";
}
