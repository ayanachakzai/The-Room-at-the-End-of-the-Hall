// These timings recreate a gentle change between static pre-generated variants.
const SCENE_CROSSFADE_MS = 1800;
const VARIANT_CROSSFADE_MS = 2500;
const VARIANT_HOLD_MS = 5000;

// This manages two image layers and automatically retains placeholders for missing images.
export class Visuals {
  // This collects the two layers, caption, and fixed scene data from the page.
  constructor(scenes) {
    this.scenes = scenes;
    this.front = document.querySelector("#image-a");
    this.back = document.querySelector("#image-b");
    this.caption = document.querySelector("#image-caption");
    this.cache = new Map();
    this.currentScene = null;
    this.currentVariant = 0;
    this.cycleTimer = null;
    this.frontIsA = true;
  }

  // This starts loading an image once and returns null when a local file is absent.
  loadImage(url) {
    if (this.cache.has(url)) {
      return this.cache.get(url);
    }

    const promise = new Promise((resolve) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = url;
    });
    this.cache.set(url, promise);
    return promise;
  }

  // This starts fetching the current scene and the next two scenes before they are needed.
  preloadFrom(sceneId) {
    const index = this.scenes.findIndex((scene) => scene.id === sceneId);

    for (let sceneIndex = index; sceneIndex < Math.min(index + 3, this.scenes.length); sceneIndex += 1) {
      for (const suffix of ["a", "b", "c"]) {
        this.loadImage(`images/${this.scenes[sceneIndex].id}-${suffix}.webp`);
      }
    }
  }

  // This changes to a new scene, keeping the previous image visible if the next one fails.
  async setScene(sceneId) {
    if (sceneId === this.currentScene) {
      return;
    }

    const scene = this.scenes.find((item) => item.id === sceneId);
    if (!scene) {
      return;
    }

    this.currentScene = sceneId;
    this.currentVariant = 0;
    window.clearTimeout(this.cycleTimer);
    this.preloadFrom(sceneId);
    await this.showVariant(scene, 0, SCENE_CROSSFADE_MS);
    this.scheduleCycle();
  }

  // This crossfades a loaded image onto the back layer or keeps the placeholder caption visible.
  async showVariant(scene, variantIndex, duration) {
    const suffix = String.fromCharCode("a".charCodeAt(0) + variantIndex);
    const image = await this.loadImage(`images/${scene.id}-${suffix}.webp`);

    if (scene.id !== this.currentScene || !image) {
      if (!image && scene.id === this.currentScene) {
        this.showPlaceholder(scene);
      }
      return false;
    }

    const frontLayer = this.frontIsA ? this.front : this.back;
    const backLayer = this.frontIsA ? this.back : this.front;
    backLayer.style.transitionDuration = `${duration}ms`;
    frontLayer.style.transitionDuration = `${duration}ms`;
    backLayer.src = image.src;
    backLayer.alt = scene.short;
    backLayer.classList.add("is-front");
    frontLayer.classList.remove("is-front");
    this.frontIsA = !this.frontIsA;
    this.caption.textContent = "";
    return true;
  }

  // This shows the required caption when no pre-generated image exists for a scene.
  showPlaceholder(scene) {
    this.front.classList.remove("is-front");
    this.back.classList.remove("is-front");
    this.caption.textContent = `[Scene image: ${scene.short}]`;
  }

  // This cycles the available variants after each hold, then continues while the scene stays active.
  scheduleCycle() {
    window.clearTimeout(this.cycleTimer);
    const scene = this.scenes.find((item) => item.id === this.currentScene);

    if (!scene) {
      return;
    }

    this.cycleTimer = window.setTimeout(async () => {
      this.currentVariant = (this.currentVariant + 1) % 3;
      const shown = await this.showVariant(scene, this.currentVariant, VARIANT_CROSSFADE_MS);

      if (!shown && this.currentVariant === 0) {
        this.showPlaceholder(scene);
      }

      if (scene.id === this.currentScene) {
        this.scheduleCycle();
      }
    }, VARIANT_HOLD_MS);
  }

  // This fades both image layers to black for the ending sequence.
  fadeToBlack() {
    window.clearTimeout(this.cycleTimer);
    this.front.style.transitionDuration = "4000ms";
    this.back.style.transitionDuration = "4000ms";
    this.front.classList.remove("is-front");
    this.back.classList.remove("is-front");
    this.caption.textContent = "";
  }
}
