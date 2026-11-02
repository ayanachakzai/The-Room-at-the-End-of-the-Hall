// This language matches the performance's British English reading.
const LANGUAGE = "en-GB";

// This checks whether a page address can request a microphone from the browser.
function hasMicrophoneAddress() {
  const { protocol, hostname } = window.location;
  return protocol === "https:"
    || (protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(hostname));
}

// These browsers expose an API that cannot reliably listen for this performance.
function isUnsupportedBrowser() {
  return navigator.userAgent.includes("OPR/") || Boolean(navigator.brave);
}

// This wraps browser speech recognition and restarts it after normal browser stops.
export class SpeechRecognitionController {
  // This creates a recognition instance only when the browser provides the API.
  constructor(callbacks = {}) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.callbacks = callbacks;
    this.unavailableReason = !hasMicrophoneAddress()
      ? "insecure"
      : (!Recognition || isUnsupportedBrowser() ? "browser" : null);
    this.available = !this.unavailableReason;
    this.stopped = true;
    this.denied = false;
    this.startedOnce = false;
    this.restartDelay = 250;
    this.networkDelay = 0;
    this.restartTimer = null;
    this.startWatchdog = null;

    if (!this.available) {
      return;
    }

    this.recognition = new Recognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.recognition.lang = LANGUAGE;
    this.addListeners();
  }

  // This forwards each current recognition result instead of the full session transcript.
  addListeners() {
    this.recognition.onstart = () => {
      this.startedOnce = true;
      this.networkDelay = 0;
      this.restartDelay = 250;
      window.clearTimeout(this.startWatchdog);
      this.callbacks.onStart?.();
    };

    this.recognition.onresult = (event) => {
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result[0].transcript.trim();

        if (result.isFinal) {
          this.networkDelay = 0;
          this.callbacks.onFinal?.(text);
        } else {
          this.callbacks.onInterim?.(text);
        }
      }
    };

    this.recognition.onerror = (event) => this.handleError(event.error);
    this.recognition.onend = () => this.restart();
  }

  // This starts recognition and ignores the harmless error from an already-running instance.
  start() {
    if (!this.available || this.denied) {
      return;
    }

    this.stopped = false;

    if (!this.startedOnce && !this.startWatchdog) {
      this.startWatchdog = window.setTimeout(() => {
        if (!this.startedOnce && !this.stopped) {
          this.failBeforeStart("timeout");
        }
      }, 4000);
    }

    try {
      this.recognition.start();
    } catch (error) {
      if (error.name !== "InvalidStateError") {
        this.failBeforeStart(error.name);
      }
    }
  }

  // This stops recognition permanently when the performance has reached its ending.
  stop() {
    this.stopped = true;
    window.clearTimeout(this.restartTimer);
    window.clearTimeout(this.startWatchdog);
    this.startWatchdog = null;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (error) {
        // A browser may reject stop when recognition never actually started.
      }
    }
  }

  // This ends a failed first start and tells the page why listening is unavailable.
  failBeforeStart(reason) {
    this.stop();
    this.callbacks.onUnavailable?.(reason);
  }

  // This reports permission errors and gradually retries temporary network errors.
  handleError(error) {
    if (error === "not-allowed" || error === "service-not-allowed") {
      this.denied = true;
      if (!this.startedOnce && error === "service-not-allowed") {
        this.failBeforeStart(error);
      } else {
        this.stop();
        this.callbacks.onError?.(error);
      }
      return;
    }

    if (error === "network") {
      if (!this.startedOnce) {
        this.failBeforeStart(error);
        return;
      }
      this.networkDelay = Math.min(this.networkDelay ? this.networkDelay * 2 : 1000, 10000);
      this.restartDelay = this.networkDelay;
      return;
    }

    if (error !== "no-speech" && error !== "aborted") {
      this.callbacks.onError?.(error);
    }
  }

  // This waits briefly before restarting so the browser never enters a tight loop.
  restart() {
    if (this.stopped || this.denied) {
      return;
    }

    const delay = this.restartDelay;
    this.restartDelay = this.networkDelay || 250;
    window.clearTimeout(this.restartTimer);
    this.restartTimer = window.setTimeout(() => this.start(), delay);
  }
}
