// This creates diagnostics only when the visitor explicitly adds ?debug=1 to the URL.
export class DebugOverlay {
  // This checks the URL before adding any debug-only DOM or keyboard behaviour.
  constructor(onNextLine) {
    this.enabled = new URLSearchParams(window.location.search).get("debug") === "1";
    this.values = {};

    if (!this.enabled) {
      return;
    }

    this.element = document.createElement("pre");
    this.element.style.position = "fixed";
    this.element.style.right = "1rem";
    this.element.style.bottom = "1rem";
    this.element.style.left = "1rem";
    this.element.style.zIndex = "10";
    this.element.style.margin = "0";
    this.element.style.color = "#8A8A8A";
    this.element.style.font = "12px monospace";
    this.element.style.pointerEvents = "none";
    document.body.append(this.element);
    window.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") {
        onNextLine();
      }
    });
  }

  // This merges new details before drawing one compact diagnostic text block.
  update(values) {
    if (!this.enabled) {
      return;
    }

    this.values = { ...this.values, ...values };
    const value = (key) => this.values[key] ?? "";
    this.element.textContent = [
      `interim: ${value("interim")}`,
      `final: ${value("final")}`,
      `line: ${value("activeLine")}/43  spoken: ${value("spokenCount")}`,
      `match: ${value("score")}  corner: ${value("corner")}`,
      `energy: ${value("energy")} tension: ${value("tension")} valence: ${value("valence")} pace: ${value("pace")}`,
    ].join("\n");
    console.log("Living Score debug", this.values);
  }
}
