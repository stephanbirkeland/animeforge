/**
 * AnimeForge Scene Loader — Asset loading and scene.json parser.
 *
 * Loads a scene definition file, resolves all referenced image assets,
 * and returns a fully-hydrated data structure ready for the runtime.
 *
 * @version 1.0.0
 * @license MIT
 */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  const TIME_KEYS = ['dawn', 'day', 'sunset', 'night'];

  /**
   * Adjacent time slots used for smart preloading.
   * If current time is 'day', preload 'dawn' and 'sunset' as well.
   * @type {Object<string, string[]>}
   */
  const ADJACENT_TIMES = {
    dawn:   ['night', 'day'],
    day:    ['dawn', 'sunset'],
    sunset: ['day', 'night'],
    night:  ['sunset', 'dawn'],
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Resolve a relative URL against a base path.
   * @param {string} base - Base URL (the scene.json URL).
   * @param {string} relative - Relative asset path.
   * @returns {string} Resolved URL.
   */
  function resolveUrl(base, relative) {
    if (/^https?:\/\/|^\/|^data:/.test(relative)) {
      return relative; // Already absolute
    }
    const parts = base.split('/');
    parts.pop(); // Remove filename
    return parts.join('/') + '/' + relative;
  }

  /**
   * Load an image and return a promise.
   * @param {string} src - Image source URL.
   * @returns {Promise<HTMLImageElement>}
   */
  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`[AnimeForge] Failed to load image: ${src}`));
      img.src = src;
    });
  }

  // ---------------------------------------------------------------------------
  // SceneLoader
  // ---------------------------------------------------------------------------

  class SceneLoader {
    /**
     * @param {string} sceneUrl - URL to the scene.json file.
     * @param {Object} [options]
     * @param {boolean} [options.lazy=false] - If true, only preload current time + adjacent.
     * @param {string}  [options.initialTime='day'] - Used with lazy loading to pick initial assets.
     */
    constructor(sceneUrl, options = {}) {
      /** @type {string} */
      this._sceneUrl = sceneUrl;

      /** @type {boolean} */
      this._lazy = options.lazy ?? false;

      /** @type {string} */
      this._initialTime = options.initialTime ?? 'day';

      /** @type {Function|null} */
      this._progressCallback = null;

      /** @type {number} Total assets to load */
      this._totalAssets = 0;

      /** @type {number} Assets loaded so far */
      this._loadedAssets = 0;

      /** @type {Map<string, HTMLImageElement>} Cache of loaded images by URL */
      this._imageCache = new Map();
    }

    /**
     * Register a progress callback.
     * @param {Function} fn - Called with { loaded: number, total: number, percent: number }.
     * @returns {SceneLoader} this (for chaining).
     */
    onProgress(fn) {
      this._progressCallback = fn;
      return this;
    }

    /**
     * Load and parse the scene definition, including all referenced assets.
     * @returns {Promise<Object>} Hydrated scene data with loaded Image objects.
     */
    async load() {
      // 1. Fetch scene.json
      const response = await fetch(this._sceneUrl);
      if (!response.ok) {
        throw new Error(`[AnimeForge] Failed to fetch scene: ${response.status} ${response.statusText}`);
      }

      /** @type {Object} */
      const raw = await response.json();
      this._validate(raw);

      // 2. Count total assets to load
      this._totalAssets = this._countAssets(raw);
      this._loadedAssets = 0;
      this._reportProgress();

      // 3. Load assets in parallel groups
      const result = {
        meta: raw.meta || {},
        layers: [],
        zones: [],
        animations: [],
        initial: raw.initial || {},
      };

      // Load layers
      if (raw.layers && Array.isArray(raw.layers)) {
        const layerPromises = raw.layers.map((layer) => this._loadLayer(layer));
        result.layers = await Promise.all(layerPromises);
      }

      // Load animations (sprite sheets)
      if (raw.animations && Array.isArray(raw.animations)) {
        const animPromises = raw.animations.map((anim) => this._loadAnimation(anim));
        result.animations = await Promise.all(animPromises);
      }

      // Parse zones (no async loading needed)
      if (raw.zones && Array.isArray(raw.zones)) {
        result.zones = raw.zones.map((zone) => this._parseZone(zone));
      }

      return result;
    }

    /**
     * Lazy-load additional time-of-day assets after initial load.
     * Call this to fill in images that were skipped during lazy loading.
     * @param {Object} sceneData - The result from load().
     * @param {string} time - Time to load assets for.
     * @returns {Promise<void>}
     */
    async loadTimeAssets(sceneData, time) {
      if (!sceneData || !sceneData.layers) return;

      const promises = [];

      for (const layer of sceneData.layers) {
        if (layer._rawImages && layer._rawImages[time] && !layer.images[time]) {
          const src = resolveUrl(this._sceneUrl, layer._rawImages[time]);
          promises.push(
            this._loadImageCached(src).then((img) => {
              layer.images[time] = img;
            })
          );
        }
      }

      if (promises.length > 0) {
        await Promise.all(promises);
      }
    }

    // ---- Private ------------------------------------------------------------

    /**
     * Basic validation of the scene JSON structure.
     * @private
     * @param {Object} raw
     */
    _validate(raw) {
      if (!raw || typeof raw !== 'object') {
        throw new Error('[AnimeForge] scene.json must be a JSON object.');
      }
      if (raw.version && raw.version !== 1) {
        console.warn(`[AnimeForge] scene.json version ${raw.version} may not be fully supported.`);
      }
    }

    /**
     * Count total image assets that need loading.
     * @private
     * @param {Object} raw
     * @returns {number}
     */
    _countAssets(raw) {
      let count = 0;

      if (raw.layers) {
        for (const layer of raw.layers) {
          if (layer.images) {
            const times = this._getTimesToLoad(layer.images);
            count += times.length;
          }
        }
      }

      if (raw.animations) {
        count += raw.animations.length;
      }

      return Math.max(count, 1);
    }

    /**
     * Determine which time keys to load based on lazy mode.
     * @private
     * @param {Object} images - { dawn: url, day: url, ... }
     * @returns {string[]}
     */
    _getTimesToLoad(images) {
      const available = Object.keys(images).filter((k) => TIME_KEYS.includes(k));

      if (!this._lazy) {
        return available;
      }

      // Lazy: load current time + adjacent
      const wanted = new Set([this._initialTime]);
      const adj = ADJACENT_TIMES[this._initialTime] || [];
      for (const t of adj) {
        wanted.add(t);
      }

      return available.filter((t) => wanted.has(t));
    }

    /**
     * Load a single layer's images.
     * @private
     * @param {Object} layerDef - Raw layer definition from scene.json.
     * @returns {Promise<Object>} Hydrated layer with Image objects.
     */
    async _loadLayer(layerDef) {
      const result = {
        depth: layerDef.depth || 'background',
        parallax_factor: layerDef.parallax_factor || 0,
        images: {},
        _rawImages: layerDef.images || {},
      };

      if (!layerDef.images) return result;

      const timesToLoad = this._getTimesToLoad(layerDef.images);
      const promises = timesToLoad.map(async (time) => {
        const src = resolveUrl(this._sceneUrl, layerDef.images[time]);
        try {
          const img = await this._loadImageCached(src);
          result.images[time] = img;
        } catch (err) {
          console.error(`[AnimeForge] Layer "${result.depth}" failed for time "${time}":`, err.message);
        }
        this._loadedAssets++;
        this._reportProgress();
      });

      await Promise.all(promises);
      return result;
    }

    /**
     * Load a single animation's sprite sheet.
     * @private
     * @param {Object} animDef - Raw animation definition.
     * @returns {Promise<Object>} Hydrated animation with loaded Image.
     */
    async _loadAnimation(animDef) {
      const result = {
        name: animDef.name,
        frame_width: animDef.frame_width,
        frame_height: animDef.frame_height,
        frame_count: animDef.frame_count,
        fps: animDef.fps ?? 12,
        loop: animDef.loop !== false,
        image: null,
      };

      if (animDef.sprite_sheet) {
        const src = resolveUrl(this._sceneUrl, animDef.sprite_sheet);
        try {
          result.image = await this._loadImageCached(src);
        } catch (err) {
          console.error(`[AnimeForge] Animation "${animDef.name}" sprite sheet failed:`, err.message);
        }
      }

      this._loadedAssets++;
      this._reportProgress();
      return result;
    }

    /**
     * Parse a zone definition (no async).
     * @private
     * @param {Object} zoneDef
     * @returns {Object}
     */
    _parseZone(zoneDef) {
      return {
        id: zoneDef.id,
        x: zoneDef.x ?? 0,
        y: zoneDef.y ?? 0,
        width: zoneDef.width ?? 0.2,
        height: zoneDef.height ?? 0.3,
        type: zoneDef.type ?? 'character',
        scale: zoneDef.scale ?? 1,
      };
    }

    /**
     * Load an image with caching to avoid duplicate requests.
     * @private
     * @param {string} src
     * @returns {Promise<HTMLImageElement>}
     */
    async _loadImageCached(src) {
      if (this._imageCache.has(src)) {
        return this._imageCache.get(src);
      }
      const img = await loadImage(src);
      this._imageCache.set(src, img);
      return img;
    }

    /**
     * Emit progress to the registered callback.
     * @private
     */
    _reportProgress() {
      if (this._progressCallback) {
        const loaded = this._loadedAssets;
        const total = this._totalAssets;
        const percent = Math.round((loaded / total) * 100);
        this._progressCallback({ loaded, total, percent });
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Expose
  // ---------------------------------------------------------------------------

  if (!global.AnimeForge) {
    global.AnimeForge = {};
  }

  /**
   * Load an AnimeForge scene definition and its assets.
   *
   * @example
   * const loader = new AnimeForge.SceneLoader('assets/scene.json');
   * loader.onProgress(({ percent }) => console.log(`${percent}%`));
   * const data = await loader.load();
   *
   * @example
   * // Lazy loading — only loads current time + adjacent
   * const loader = new AnimeForge.SceneLoader('assets/scene.json', {
   *   lazy: true,
   *   initialTime: 'night'
   * });
   * const data = await loader.load();
   * // Later, load remaining assets:
   * await loader.loadTimeAssets(data, 'day');
   */
  global.AnimeForge.SceneLoader = SceneLoader;

})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
