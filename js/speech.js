// This language matches the performance's British English reading.
const LANGUAGE = "en-GB";

// This wraps browser speech recognition and restarts it after normal browser stops.
export class SpeechRecognitionController {
  // This creates a recognition instance only when the browser provides the API.
  constructor(callbacks = {}) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.callbacks = callbacks;
    this.available = Boolean(Recognition);
    this.stopped = true;
    this.denied = false;
    this.restartDelay = 250;
    this.networkDelay = 0;
    this.restartTimer = null;

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

    try {
      this.recognition.start();
    } catch (error) {
      if (error.name !== "InvalidStateError") {
        this.callbacks.onError?.(error.name);
      }
    }
  }

  // This stops recognition permanently when the performance has reached its ending.
  stop() {
    this.stopped = true;
    window.clearTimeout(this.restartTimer);
    this.recognition?.stop();
  }

  // This reports permission errors and gradually retries temporary network errors.
  handleError(error) {
    if (error === "not-allowed" || error === "service-not-allowed") {
      this.denied = true;
      this.stopped = true;
      this.callbacks.onError?.(error);
      return;
    }

    if (error === "network") {
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
