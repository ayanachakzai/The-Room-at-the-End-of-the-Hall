import { DebugOverlay } from "./debug.js";
import { Music } from "./music.js";
import { SpeechRecognitionController } from "./speech.js";
import { Story } from "./story.js";
import { Visuals } from "./visuals.js";

// This is the public repository containing the website and copied live system.
const REPOSITORY_URL = "https://github.com/ayanachakzai/The-Room-at-the-End-of-the-Hall";

// This loads the fixed story data that drives every browser-side response.
async function loadStory() {
  const response = await fetch("data/story.json");

  if (!response.ok) {
    throw new Error("The story data could not be loaded.");
  }

  return response.json();
}

// This switches screens using the shared CSS fade without adding interface controls.
function showScreen(screen) {
  document.querySelectorAll(".screen").forEach((item) => item.classList.remove("is-visible"));
  screen.classList.add("is-visible");
}

// This accepts pointer activation and the two keyboard keys required by the brief.
function isEnterAction(event) {
  return event.type === "click" || event.key === "Enter" || event.key === " ";
}

// This creates and updates visible word spans while keeping already-lit words stable.
function createStoryView() {
  const previous = document.querySelector("#previous-line");
  const current = document.querySelector("#current-line");
  let renderedIndex = -1;
  let words = [];

  return (state) => {
    previous.textContent = state.previousLine;

    if (state.finished || !state.line) {
      current.textContent = "";
      words = [];
      return;
    }

    if (renderedIndex !== state.activeLine) {
      current.classList.add("is-changing");
      window.setTimeout(() => {
        current.textContent = "";
        words = state.line.text.split(/\s+/).map((word) => {
          const span = document.createElement("span");
          span.className = "word";
          span.textContent = word;
          current.append(span);
          return span;
        });
        renderedIndex = state.activeLine;
        words.forEach((word, index) => word.classList.toggle("is-spoken", index < state.spokenCount));
        current.classList.remove("is-changing");
      }, renderedIndex < 0 ? 0 : 400);
      return;
    }

    words.forEach((word, index) => word.classList.toggle("is-spoken", index < state.spokenCount));
  };
}

// This hides the pointer after three seconds of stillness during the performance.
function addCursorTimer(performanceScreen) {
  let timer;

  const resetCursor = () => {
    document.body.classList.remove("performance-cursor-hidden");
    window.clearTimeout(timer);

    if (performanceScreen.classList.contains("is-visible")) {
      timer = window.setTimeout(() => document.body.classList.add("performance-cursor-hidden"), 3000);
    }
  };

  window.addEventListener("pointermove", resetCursor);
}

// This starts the website after data has loaded and connects its small browser modules.
async function main() {
  const storyData = await loadStory();
  const titleScreen = document.querySelector("#title-screen");
  const beginScreen = document.querySelector("#begin-screen");
  const performanceScreen = document.querySelector("#performance-screen");
  const endScreen = document.querySelector("#end-screen");
  const status = document.querySelector("#status-line");
  const endLink = endScreen.querySelector("a");
  endLink.href = REPOSITORY_URL;
  let started = false;
  let ending = false;
  let debug;
  let music;
  let visuals;
  let speech;
  let story;

  // This waits at the final sentence before completing the specified fade sequence.
  const finishPerformance = () => {
    if (ending) {
      return;
    }

    ending = true;
    window.setTimeout(() => {
      music.fadeOut();
      visuals.fadeToBlack();
      speech.stop();
      window.setTimeout(() => {
        music.stop();
        showScreen(endScreen);
      }, 5000);
    }, 6000);
  };

  // This renders normal story state and adds diagnostics only in explicit debug mode.
  const renderStory = createStoryView();
  story = new Story(storyData.lines, {
    onView: (state) => {
      renderStory(state);
      debug?.update({
        activeLine: state.finished ? 43 : state.activeLine + 1,
        spokenCount: state.spokenCount,
        score: state.lastBestScore.toFixed(3),
      });
    },
    onCue: (line) => {
      music.applyCue(line);
      visuals.setScene(line.sceneId);
    },
    onFinish: finishPerformance,
  });
  debug = new DebugOverlay(() => story.completeForDebug());
  music = new Music(storyData.music, (values) => debug?.update({
    corner: values.corner,
    energy: values.energy.toFixed(2),
    tension: values.tension.toFixed(2),
    valence: values.valence.toFixed(2),
    pace: values.pace.toFixed(2),
  }));
  visuals = new Visuals(storyData.scenes);
  speech = new SpeechRecognitionController({
    onInterim: (text) => {
      debug?.update({ interim: text });
      story.processTranscript(text, false);
    },
    onFinal: (text) => {
      debug?.update({ final: text });
      story.processTranscript(text, true);
    },
    onError: (error) => {
      if (error === "not-allowed" || error === "service-not-allowed") {
        status.textContent = "Microphone access is needed. Allow it in your browser settings and reload the page.";
      }
    },
  });
  addCursorTimer(performanceScreen);

  // This moves from the title into the required microphone and headphone guidance.
  const enterBegin = (event) => {
    if (!isEnterAction(event)) {
      return;
    }

    event.preventDefault();
    showScreen(beginScreen);
    beginScreen.focus();
  };

  // This uses the gesture to unlock sound, request speech, cue line one, and reveal the room.
  const startPerformance = async (event) => {
    if (!isEnterAction(event) || started) {
      return;
    }

    event.preventDefault();
    started = true;

    if (!speech.available) {
      status.textContent = "This browser can't listen. Please open this page in Chrome, Edge or Safari.";
      visuals.setScene(storyData.lines[0].sceneId);
      showScreen(performanceScreen);
      return;
    }

    const audioStart = Tone.start();
    speech.start();
    await audioStart;
    await music.start(storyData.lines[0]);
    visuals.setScene(storyData.lines[0].sceneId);
    story.start();
    showScreen(performanceScreen);
  };

  titleScreen.addEventListener("click", enterBegin);
  titleScreen.addEventListener("keydown", enterBegin);
  beginScreen.addEventListener("click", startPerformance);
  beginScreen.addEventListener("keydown", startPerformance);
  titleScreen.focus();
}

// This shows loading failures in the console because the performance cannot start without data.
main().catch((error) => console.error(error));
