/**
 * AnimeForge Runtime — Canvas 2D Scene Renderer
 *
 * Renders layered anime-style scenes with character sprite animation,
 * time-of-day lighting, weather particle effects, and zone management.
 *
 * @version 1.0.0
 * @license MIT
 */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------------------
  // EventEmitter — lightweight pub/sub
  // ---------------------------------------------------------------------------

  class EventEmitter {
    constructor() {
      /** @type {Map<string, Set<Function>>} */
      this._listeners = new Map();
    }

    /**
     * Subscribe to an event.
     * @param {string} event
     * @param {Function} fn
     * @returns {Function} Unsubscribe function.
     */
    on(event, fn) {
      if (!this._listeners.has(event)) {
        this._listeners.set(event, new Set());
      }
      this._listeners.get(event).add(fn);
      return () => this.off(event, fn);
    }

    /**
     * Unsubscribe from an event.
     * @param {string} event
     * @param {Function} fn
     */
    off(event, fn) {
      const set = this._listeners.get(event);
      if (set) {
        set.delete(fn);
        if (set.size === 0) this._listeners.delete(event);
      }
    }

    /**
     * Subscribe to an event once.
     * @param {string} event
     * @param {Function} fn
     * @returns {Function} Unsubscribe function.
     */
    once(event, fn) {
      const wrapped = (...args) => {
        this.off(event, wrapped);
        fn.apply(null, args);
      };
      return this.on(event, wrapped);
    }

    /**
     * Emit an event.
     * @param {string} event
     * @param {...*} args
     */
    emit(event, ...args) {
      const set = this._listeners.get(event);
      if (set) {
        for (const fn of set) {
          try {
            fn(...args);
          } catch (err) {
            console.error(`[AnimeForge] Error in "${event}" listener:`, err);
          }
        }
      }
    }

    /** Remove all listeners. */
    removeAll() {
      this._listeners.clear();
    }
  }

  // ---------------------------------------------------------------------------
  // LayerManager — background compositing with cross-fade
  // ---------------------------------------------------------------------------

  class LayerManager {
    /**
     * @param {SceneRenderer} renderer
     */
    constructor(renderer) {
      this._renderer = renderer;

      /** @type {Object<string, Object<string, HTMLImageElement>>} */
      this._layers = {}; // e.g. { background: { day: Image, night: Image, ... } }

      /** @type {string} */
      this._currentTime = 'day';
      /** @type {string|null} */
      this._previousTime = null;

      /** Cross-fade progress 0..1 (1 = fully transitioned) */
      this._fadeProgress = 1;
      this._fadeDuration = 2000; // ms
      this._fadeElapsed = 0;
    }

    /**
     * Register a layer image for a given depth and time of day.
     * @param {string} depth   - 'background' | 'midground' | 'foreground'
     * @param {string} time    - 'dawn' | 'day' | 'sunset' | 'night'
     * @param {HTMLImageElement} image
     * @param {number} [parallaxFactor=0] - Reserved for future parallax support.
     */
    addLayer(depth, time, image, parallaxFactor = 0) {
      if (!this._layers[depth]) {
        this._layers[depth] = {};
      }
      this._layers[depth][time] = image;
      // Store parallax factor on the image for future use
      image._parallaxFactor = parallaxFactor;
    }

    /**
     * Begin a cross-fade transition to a new time of day.
     * @param {string} newTime
     * @param {number} [duration=2000]
     */
    transitionTo(newTime, duration = 2000) {
      if (newTime === this._currentTime && this._fadeProgress >= 1) return;
      this._previousTime = this._currentTime;
      this._currentTime = newTime;
      this._fadeDuration = duration;
      this._fadeElapsed = 0;
      this._fadeProgress = 0;
    }

    /**
     * Update cross-fade progress.
     * @param {number} dt - Delta time in ms.
     */
    update(dt) {
      if (this._fadeProgress < 1) {
        this._fadeElapsed += dt;
        this._fadeProgress = Math.min(this._fadeElapsed / this._fadeDuration, 1);
        // Ease-in-out for smooth transition
        this._fadeProgress = this._easeInOut(this._fadeProgress);
      }
    }

    /**
     * Draw a specific depth layer to the canvas.
     * @param {CanvasRenderingContext2D} ctx
     * @param {string} depth
     * @param {number} canvasW
     * @param {number} canvasH
     */
    draw(ctx, depth, canvasW, canvasH) {
      const layerSet = this._layers[depth];
      if (!layerSet) return;

      // If we are mid-transition, draw previous layer then blend new layer on top
      if (this._fadeProgress < 1 && this._previousTime) {
        const prevImg = layerSet[this._previousTime];
        const currImg = layerSet[this._currentTime];

        if (prevImg) {
          ctx.globalAlpha = 1;
          this._drawImage(ctx, prevImg, canvasW, canvasH);
        }
        if (currImg) {
          ctx.globalAlpha = this._fadeProgress;
          this._drawImage(ctx, currImg, canvasW, canvasH);
          ctx.globalAlpha = 1;
        }
      } else {
        const img = layerSet[this._currentTime];
        if (img) {
          ctx.globalAlpha = 1;
          this._drawImage(ctx, img, canvasW, canvasH);
        }
      }
    }

    /** @returns {string} Current time key. */
    get currentTime() {
      return this._currentTime;
    }

    /** @returns {boolean} Whether a transition is in progress. */
    get isTransitioning() {
      return this._fadeProgress < 1;
    }

    /**
     * Draw an image scaled to cover the canvas (cover mode).
     * @private
     */
    _drawImage(ctx, img, canvasW, canvasH) {
      const imgAspect = img.naturalWidth / img.naturalHeight;
      const canAspect = canvasW / canvasH;
      let sx = 0, sy = 0, sw = img.naturalWidth, sh = img.naturalHeight;

      if (imgAspect > canAspect) {
        // Image is wider — crop sides
        sw = img.naturalHeight * canAspect;
        sx = (img.naturalWidth - sw) / 2;
      } else {
        // Image is taller — crop top/bottom
        sh = img.naturalWidth / canAspect;
        sy = (img.naturalHeight - sh) / 2;
      }

      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvasW, canvasH);
    }

    /** Smooth ease-in-out curve. @private */
    _easeInOut(t) {
      return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    }
  }

  // ---------------------------------------------------------------------------
  // CharacterRenderer — sprite sheet playback
  // ---------------------------------------------------------------------------

  class CharacterRenderer {
    /**
     * @param {SceneRenderer} renderer
     */
    constructor(renderer) {
      this._renderer = renderer;

      /** @type {Map<string, Object>} animation name -> config */
      this._animations = new Map();

      /** @type {string|null} */
      this._currentAnimation = null;
      /** @type {string|null} */
      this._previousAnimation = null;

      this._frame = 0;
      this._frameTimer = 0;
      this._fps = 12;
      this._loop = true;
      this._finished = false;

      // Cross-fade between animation states
      this._crossfadeProgress = 1;
      this._crossfadeDuration = 300;
      this._crossfadeElapsed = 0;
      this._prevFrame = 0;
    }

    /**
     * Register an animation.
     * @param {string} name       - Animation identifier.
     * @param {HTMLImageElement} spriteSheet - Horizontal strip of frames.
     * @param {Object} config
     * @param {number} config.frameWidth
     * @param {number} config.frameHeight
     * @param {number} config.frameCount
     * @param {number} [config.fps=12]
     * @param {boolean} [config.loop=true]
     */
    addAnimation(name, spriteSheet, config) {
      this._animations.set(name, {
        image: spriteSheet,
        frameWidth: config.frameWidth,
        frameHeight: config.frameHeight,
        frameCount: config.frameCount,
        fps: config.fps ?? 12,
        loop: config.loop !== false,
      });
    }

    /**
     * Play an animation by name with optional cross-fade.
     * @param {string} name
     * @param {Object} [opts]
     * @param {number} [opts.crossfadeDuration=300]
     */
    play(name, opts = {}) {
      if (!this._animations.has(name)) {
        console.warn(`[AnimeForge] Animation "${name}" not found.`);
        return;
      }
      if (name === this._currentAnimation && !this._finished) return;

      this._previousAnimation = this._currentAnimation;
      this._prevFrame = this._frame;
      this._currentAnimation = name;

      const anim = this._animations.get(name);
      this._fps = anim.fps;
      this._loop = anim.loop;
      this._frame = 0;
      this._frameTimer = 0;
      this._finished = false;

      this._crossfadeDuration = opts.crossfadeDuration ?? 300;
      this._crossfadeElapsed = 0;
      this._crossfadeProgress = this._previousAnimation ? 0 : 1;

      this._renderer._emitter.emit('animationStart', name);
    }

    /**
     * Transition from one animation to another (convenience wrapper).
     * @param {string} from
     * @param {string} to
     * @param {Object} [opts]
     * @param {number} [opts.duration=500]
     */
    transition(from, to, opts = {}) {
      if (this._currentAnimation !== from) {
        this.play(from);
      }
      // Let one frame render, then cross-fade to target
      this._pendingTransition = { to, duration: opts.duration ?? 500 };
    }

    /**
     * Advance frame and cross-fade timers.
     * @param {number} dt - Delta time in ms.
     */
    update(dt) {
      // Handle pending transition
      if (this._pendingTransition) {
        const pt = this._pendingTransition;
        this._pendingTransition = null;
        this.play(pt.to, { crossfadeDuration: pt.duration });
      }

      if (!this._currentAnimation) return;

      const anim = this._animations.get(this._currentAnimation);
      if (!anim || this._finished) return;

      // Advance frame
      this._frameTimer += dt;
      const frameDuration = 1000 / this._fps;
      while (this._frameTimer >= frameDuration) {
        this._frameTimer -= frameDuration;
        this._frame++;

        if (this._frame >= anim.frameCount) {
          if (this._loop) {
            this._frame = 0;
          } else {
            this._frame = anim.frameCount - 1;
            this._finished = true;
            this._renderer._emitter.emit('animationComplete', this._currentAnimation);
          }
        }
      }

      // Advance cross-fade
      if (this._crossfadeProgress < 1) {
        this._crossfadeElapsed += dt;
        this._crossfadeProgress = Math.min(this._crossfadeElapsed / this._crossfadeDuration, 1);
      }
    }

    /**
     * Draw the character sprite.
     * @param {CanvasRenderingContext2D} ctx
     * @param {number} x - Destination X on canvas.
     * @param {number} y - Destination Y on canvas.
     * @param {number} [scale=1]
     */
    draw(ctx, x, y, scale = 1) {
      if (!this._currentAnimation) return;

      const currAnim = this._animations.get(this._currentAnimation);
      if (!currAnim) return;

      const dw = currAnim.frameWidth * scale;
      const dh = currAnim.frameHeight * scale;

      // Draw previous animation fading out during cross-fade
      if (this._crossfadeProgress < 1 && this._previousAnimation) {
        const prevAnim = this._animations.get(this._previousAnimation);
        if (prevAnim) {
          ctx.globalAlpha = 1 - this._crossfadeProgress;
          this._drawFrame(ctx, prevAnim, this._prevFrame, x, y, dw, dh);
        }
      }

      // Draw current animation
      ctx.globalAlpha = this._crossfadeProgress < 1 ? this._crossfadeProgress : 1;
      this._drawFrame(ctx, currAnim, this._frame, x, y, dw, dh);
      ctx.globalAlpha = 1;
    }

    /** @private */
    _drawFrame(ctx, anim, frame, x, y, dw, dh) {
      const sx = frame * anim.frameWidth;
      ctx.drawImage(
        anim.image,
        sx, 0, anim.frameWidth, anim.frameHeight,
        x, y, dw, dh
      );
    }

    /** @returns {string|null} Currently playing animation name. */
    get currentAnimation() {
      return this._currentAnimation;
    }

    /** @returns {boolean} Whether the current animation has finished (one-shot). */
    get isFinished() {
      return this._finished;
    }
  }

  // ---------------------------------------------------------------------------
  // Particle — single particle data
  // ---------------------------------------------------------------------------

  class Particle {
    constructor() {
      this.x = 0;
      this.y = 0;
      this.vx = 0;
      this.vy = 0;
      this.size = 2;
      this.rotation = 0;
      this.rotationSpeed = 0;
      this.opacity = 1;
      this.life = 0;
      this.maxLife = 0;
      this.active = false;
      this.color = '#ffffff';
      /** @type {string|null} Extra data for type-specific rendering */
      this.type = null;
    }

    reset() {
      this.x = 0;
      this.y = 0;
      this.vx = 0;
      this.vy = 0;
      this.size = 2;
      this.rotation = 0;
      this.rotationSpeed = 0;
      this.opacity = 1;
      this.life = 0;
      this.maxLife = 0;
      this.active = false;
      this.color = '#ffffff';
      this.type = null;
    }
  }

  // ---------------------------------------------------------------------------
  // EffectManager — particle system for weather effects
  // ---------------------------------------------------------------------------

  class EffectManager {
    /**
     * @param {SceneRenderer} renderer
     */
    constructor(renderer) {
      this._renderer = renderer;

      /** @type {string} 'clear' | 'rain' | 'snow' | 'fog' | 'sun' */
      this._weather = 'clear';

      /** Particle pool */
      this._poolSize = 600;
      /** @type {Particle[]} */
      this._pool = [];
      for (let i = 0; i < this._poolSize; i++) {
        this._pool.push(new Particle());
      }

      this._spawnTimer = 0;
      this._fogOpacity = 0;
      this._targetFogOpacity = 0;

      // Sun ray config
      this._sunRays = [];
      this._sunRayTimer = 0;
    }

    /**
     * Set the active weather effect.
     * @param {string} weather
     */
    setWeather(weather) {
      const prev = this._weather;
      this._weather = weather;

      // Clear all active particles on weather change
      for (const p of this._pool) {
        p.active = false;
      }
      this._sunRays = [];

      // Set fog target
      this._targetFogOpacity = weather === 'fog' ? 0.35 : 0;

      if (weather === 'sun') {
        this._initSunRays();
      }

      return prev;
    }

    /**
     * @param {number} dt - Delta time in ms.
     * @param {number} canvasW
     * @param {number} canvasH
     */
    update(dt, canvasW, canvasH) {
      const dtSec = dt / 1000;

      // Fog fading
      if (this._weather === 'fog') {
        this._fogOpacity += (this._targetFogOpacity - this._fogOpacity) * dtSec * 2;
      } else {
        this._fogOpacity += (0 - this._fogOpacity) * dtSec * 3;
      }

      // Spawn new particles
      this._spawnTimer += dt;
      const spawnInterval = this._getSpawnInterval();
      while (this._spawnTimer >= spawnInterval && spawnInterval > 0) {
        this._spawnTimer -= spawnInterval;
        this._spawnParticle(canvasW, canvasH);
      }

      // Update active particles
      for (const p of this._pool) {
        if (!p.active) continue;

        p.x += p.vx * dtSec;
        p.y += p.vy * dtSec;
        p.rotation += p.rotationSpeed * dtSec;
        p.life += dt;

        // Type-specific behaviour
        if (p.type === 'snow') {
          // Gentle horizontal sway
          p.x += Math.sin(p.life * 0.002 + p.rotation) * 0.3;
        } else if (p.type === 'leaf') {
          // Tumbling sway
          p.x += Math.sin(p.life * 0.001 + p.y * 0.01) * 0.5;
          p.vy += 5 * dtSec; // slight gravity
          if (p.vy > 80) p.vy = 80;
        }

        // Fade out near end of life
        if (p.maxLife > 0) {
          const lifeRatio = p.life / p.maxLife;
          if (lifeRatio > 0.8) {
            p.opacity = 1 - (lifeRatio - 0.8) / 0.2;
          }
        }

        // Deactivate if off-screen or expired
        if (
          p.y > canvasH + 20 ||
          p.x < -20 ||
          p.x > canvasW + 20 ||
          (p.maxLife > 0 && p.life >= p.maxLife)
        ) {
          p.active = false;
        }
      }

      // Update sun rays
      if (this._weather === 'sun') {
        this._updateSunRays(dt, canvasW, canvasH);
      }
    }

    /**
     * Draw all active particles and weather effects.
     * @param {CanvasRenderingContext2D} ctx
     * @param {number} canvasW
     * @param {number} canvasH
     */
    draw(ctx, canvasW, canvasH) {
      // Draw sun rays behind particles
      if (this._weather === 'sun' || this._sunRays.length > 0) {
        this._drawSunRays(ctx, canvasW, canvasH);
      }

      // Draw particles
      for (const p of this._pool) {
        if (!p.active) continue;

        ctx.save();
        ctx.globalAlpha = p.opacity;

        if (p.type === 'rain') {
          this._drawRainDrop(ctx, p);
        } else if (p.type === 'snow') {
          this._drawSnowFlake(ctx, p);
        } else if (p.type === 'leaf') {
          this._drawLeaf(ctx, p);
        } else if (p.type === 'rain_splash') {
          this._drawSplash(ctx, p);
        }

        ctx.restore();
      }

      // Draw fog overlay
      if (this._fogOpacity > 0.005) {
        ctx.save();
        ctx.globalAlpha = this._fogOpacity;
        ctx.fillStyle = '#c8c8d0';
        ctx.fillRect(0, 0, canvasW, canvasH);
        ctx.restore();
      }
    }

    /** @returns {string} Current weather. */
    get weather() {
      return this._weather;
    }

    // ---- Private helpers ---------------------------------------------------

    /** @private */
    _getSpawnInterval() {
      switch (this._weather) {
        case 'rain':  return 8;   // very frequent
        case 'snow':  return 40;
        case 'leaves': return 120;
        default: return 0;        // no spawning
      }
    }

    /** @private */
    _acquireParticle() {
      for (const p of this._pool) {
        if (!p.active) {
          p.reset();
          p.active = true;
          return p;
        }
      }
      return null; // pool exhausted
    }

    /** @private */
    _spawnParticle(canvasW, canvasH) {
      const p = this._acquireParticle();
      if (!p) return;

      switch (this._weather) {
        case 'rain':
          this._initRain(p, canvasW, canvasH);
          break;
        case 'snow':
          this._initSnow(p, canvasW, canvasH);
          break;
        case 'leaves':
          this._initLeaf(p, canvasW, canvasH);
          break;
        default:
          p.active = false;
      }
    }

    /** @private */
    _initRain(p, canvasW, _canvasH) {
      p.type = 'rain';
      p.x = Math.random() * (canvasW + 60) - 30;
      p.y = -10;
      p.vx = -20 + Math.random() * -30;   // slight angle
      p.vy = 400 + Math.random() * 200;
      p.size = 1.5 + Math.random() * 1.5;
      p.opacity = 0.3 + Math.random() * 0.4;
      p.color = '#a0b8d0';
      p.maxLife = 0; // die when off-screen
    }

    /** @private */
    _initSnow(p, canvasW, _canvasH) {
      p.type = 'snow';
      p.x = Math.random() * canvasW;
      p.y = -10;
      p.vx = -10 + Math.random() * 20;
      p.vy = 30 + Math.random() * 40;
      p.size = 2 + Math.random() * 4;
      p.opacity = 0.5 + Math.random() * 0.5;
      p.rotation = Math.random() * Math.PI * 2;
      p.rotationSpeed = (Math.random() - 0.5) * 2;
      p.color = '#ffffff';
      p.maxLife = 0;
    }

    /** @private */
    _initLeaf(p, canvasW, _canvasH) {
      p.type = 'leaf';
      p.x = Math.random() * canvasW;
      p.y = -15;
      p.vx = 10 + Math.random() * 30;
      p.vy = 20 + Math.random() * 30;
      p.size = 4 + Math.random() * 6;
      p.opacity = 0.7 + Math.random() * 0.3;
      p.rotation = Math.random() * Math.PI * 2;
      p.rotationSpeed = (Math.random() - 0.5) * 4;
      p.maxLife = 6000 + Math.random() * 4000;

      // Seasonal leaf colors
      const season = this._renderer._season;
      const colors = {
        spring: ['#7ecf7e', '#a8e6a8', '#d4f5d4'],
        summer: ['#4a9e4a', '#6cb86c', '#3d8b3d'],
        fall:   ['#d4763a', '#c94c2e', '#e8a840', '#a83232'],
        winter: ['#8899aa', '#99aabb', '#7788aa'],
      };
      const palette = colors[season] || colors.fall;
      p.color = palette[Math.floor(Math.random() * palette.length)];
    }

    /** @private */
    _drawRainDrop(ctx, p) {
      ctx.strokeStyle = p.color;
      ctx.lineWidth = p.size * 0.6;
      ctx.lineCap = 'round';
      ctx.beginPath();
      // Rain streak — short angled line
      const len = p.size * 6;
      const angle = Math.atan2(p.vy, p.vx);
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - Math.cos(angle) * len, p.y - Math.sin(angle) * len);
      ctx.stroke();

      // Spawn splash when near bottom
      const canvasH = this._renderer._canvas.height;
      if (p.y > canvasH - 20 && Math.random() < 0.3) {
        this._spawnSplash(p.x, canvasH - 5);
      }
    }

    /** @private */
    _spawnSplash(x, y) {
      const splash = this._acquireParticle();
      if (!splash) return;
      splash.type = 'rain_splash';
      splash.x = x;
      splash.y = y;
      splash.size = 2 + Math.random() * 2;
      splash.opacity = 0.4;
      splash.maxLife = 200;
      splash.life = 0;
      splash.vx = 0;
      splash.vy = 0;
      splash.color = '#a0b8d0';
    }

    /** @private */
    _drawSplash(ctx, p) {
      const progress = p.life / p.maxLife;
      const radius = p.size * (1 + progress * 2);
      ctx.strokeStyle = p.color;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.ellipse(p.x, p.y, radius, radius * 0.4, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    /** @private */
    _drawSnowFlake(ctx, p) {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(0, 0, p.size, 0, Math.PI * 2);
      ctx.fill();
      // Small cross detail for larger flakes
      if (p.size > 3) {
        ctx.strokeStyle = 'rgba(200, 210, 230, 0.5)';
        ctx.lineWidth = 0.5;
        const arm = p.size * 0.7;
        ctx.beginPath();
        ctx.moveTo(-arm, 0); ctx.lineTo(arm, 0);
        ctx.moveTo(0, -arm); ctx.lineTo(0, arm);
        ctx.stroke();
      }
      ctx.restore();
    }

    /** @private */
    _drawLeaf(ctx, p) {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.fillStyle = p.color;
      // Simple leaf shape using bezier curves
      ctx.beginPath();
      ctx.moveTo(0, -p.size);
      ctx.bezierCurveTo(p.size, -p.size * 0.5, p.size, p.size * 0.5, 0, p.size);
      ctx.bezierCurveTo(-p.size, p.size * 0.5, -p.size, -p.size * 0.5, 0, -p.size);
      ctx.fill();
      // Leaf vein
      ctx.strokeStyle = 'rgba(0,0,0,0.15)';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(0, -p.size * 0.8);
      ctx.lineTo(0, p.size * 0.8);
      ctx.stroke();
      ctx.restore();
    }

    /** @private */
    _initSunRays() {
      this._sunRays = [];
      for (let i = 0; i < 5; i++) {
        this._sunRays.push({
          x: Math.random(),       // normalized position
          width: 40 + Math.random() * 80,
          opacity: 0,
          targetOpacity: 0.06 + Math.random() * 0.08,
          phase: Math.random() * Math.PI * 2,
        });
      }
    }

    /** @private */
    _updateSunRays(dt, _canvasW, _canvasH) {
      for (const ray of this._sunRays) {
        ray.opacity += (ray.targetOpacity - ray.opacity) * (dt / 1000) * 0.5;
        ray.phase += dt * 0.0003;
      }
    }

    /** @private */
    _drawSunRays(ctx, canvasW, canvasH) {
      for (const ray of this._sunRays) {
        if (ray.opacity < 0.002) continue;
        const x = ray.x * canvasW;
        const sway = Math.sin(ray.phase) * 20;
        const grad = ctx.createLinearGradient(x + sway, 0, x + sway, canvasH);
        grad.addColorStop(0, `rgba(255, 255, 200, ${ray.opacity})`);
        grad.addColorStop(1, 'rgba(255, 255, 200, 0)');
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(x + sway - ray.width / 2, 0);
        ctx.lineTo(x + sway + ray.width / 2, 0);
        ctx.lineTo(x + sway + ray.width, canvasH);
        ctx.lineTo(x + sway - ray.width, canvasH);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
    }
  }

  // ---------------------------------------------------------------------------
  // ZoneManager — positional zones for characters and animated objects
  // ---------------------------------------------------------------------------

  class ZoneManager {
    /**
     * @param {SceneRenderer} renderer
     */
    constructor(renderer) {
      this._renderer = renderer;

      /** @type {Map<string, Object>} zone id -> zone data */
      this._zones = new Map();

      /** @type {Map<string, string>} zone id -> active animation name */
      this._zoneAnimations = new Map();
    }

    /**
     * Register a zone.
     * @param {string} id
     * @param {Object} config
     * @param {number} config.x - Normalized x (0..1) relative to canvas.
     * @param {number} config.y - Normalized y (0..1).
     * @param {number} config.width - Normalized width.
     * @param {number} config.height - Normalized height.
     * @param {string} [config.type='character'] - 'character' | 'prop' | 'effect'
     * @param {number} [config.scale=1]
     */
    addZone(id, config) {
      this._zones.set(id, {
        x: config.x ?? 0,
        y: config.y ?? 0,
        width: config.width ?? 0.2,
        height: config.height ?? 0.3,
        type: config.type ?? 'character',
        scale: config.scale ?? 1,
        visible: true,
      });
    }

    /**
     * Set which animation plays inside a zone.
     * @param {string} zoneId
     * @param {string} animationName
     */
    setZoneAnimation(zoneId, animationName) {
      if (!this._zones.has(zoneId)) {
        console.warn(`[AnimeForge] Zone "${zoneId}" not found.`);
        return;
      }
      this._zoneAnimations.set(zoneId, animationName);
    }

    /**
     * Get the canvas-pixel position for a zone.
     * @param {string} zoneId
     * @param {number} canvasW
     * @param {number} canvasH
     * @returns {{ x: number, y: number, scale: number } | null}
     */
    getZonePosition(zoneId, canvasW, canvasH) {
      const zone = this._zones.get(zoneId);
      if (!zone || !zone.visible) return null;
      return {
        x: zone.x * canvasW,
        y: zone.y * canvasH,
        scale: zone.scale,
      };
    }

    /**
     * Get the character zone (first zone of type 'character').
     * @returns {string|null}
     */
    getCharacterZoneId() {
      for (const [id, zone] of this._zones) {
        if (zone.type === 'character') return id;
      }
      return null;
    }

    /** @returns {Map<string, Object>} */
    get zones() {
      return this._zones;
    }

    /** @returns {Map<string, string>} */
    get zoneAnimations() {
      return this._zoneAnimations;
    }
  }

  // ---------------------------------------------------------------------------
  // LightingManager — time-of-day overlay blending
  // ---------------------------------------------------------------------------

  class LightingManager {
    constructor() {
      /** @type {Object<string, number[]>} time -> [r, g, b, a] */
      this._presets = {
        dawn:    [255, 180, 200, 0.15],
        day:     [255, 255, 240, 0.05],
        sunset:  [255, 140,  60, 0.20],
        night:   [ 30,  40,  80, 0.30],
      };

      this._current = [...this._presets.day];
      this._target  = [...this._presets.day];
      this._speed   = 2; // transition speed (units/sec)
    }

    /**
     * Set the target lighting preset.
     * @param {string} time - 'dawn' | 'day' | 'sunset' | 'night'
     * @param {number} [speed=2] - Transition speed multiplier.
     */
    setTime(time, speed = 2) {
      const preset = this._presets[time];
      if (!preset) {
        console.warn(`[AnimeForge] Unknown lighting preset "${time}".`);
        return;
      }
      this._target = [...preset];
      this._speed = speed;
    }

    /**
     * Register a custom lighting preset.
     * @param {string} name
     * @param {number[]} rgba - [r, g, b, a]
     */
    addPreset(name, rgba) {
      this._presets[name] = [...rgba];
    }

    /**
     * Interpolate toward target color.
     * @param {number} dt - Delta time in ms.
     */
    update(dt) {
      const dtSec = dt / 1000;
      const factor = Math.min(this._speed * dtSec, 1);
      for (let i = 0; i < 4; i++) {
        this._current[i] += (this._target[i] - this._current[i]) * factor;
      }
    }

    /**
     * Apply the lighting overlay.
     * @param {CanvasRenderingContext2D} ctx
     * @param {number} canvasW
     * @param {number} canvasH
     */
    draw(ctx, canvasW, canvasH) {
      const [r, g, b, a] = this._current;
      if (a < 0.002) return;
      ctx.save();
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${a.toFixed(4)})`;
      ctx.fillRect(0, 0, canvasW, canvasH);
      ctx.restore();
    }

    /** @returns {number[]} Current RGBA values. */
    get currentColor() {
      return [...this._current];
    }
  }

  // ---------------------------------------------------------------------------
  // SceneRenderer — main orchestrator and public API
  // ---------------------------------------------------------------------------

  class SceneRenderer {
    /**
     * Create a new SceneRenderer.
     * @param {string|HTMLCanvasElement} canvasSelector - CSS selector or canvas element.
     * @param {string} sceneUrl - URL to scene.json.
     * @param {Object} [options]
     * @param {number} [options.width]   - Canvas width (default: element size or 960).
     * @param {number} [options.height]  - Canvas height (default: element size or 540).
     * @param {boolean} [options.autoTime=false] - Auto-advance time based on real clock.
     * @param {number} [options.transitionDuration=2000] - Default cross-fade duration in ms.
     */
    constructor(canvasSelector, sceneUrl, options = {}) {
      /** @type {HTMLCanvasElement} */
      this._canvas = typeof canvasSelector === 'string'
        ? document.querySelector(canvasSelector)
        : canvasSelector;

      if (!this._canvas || this._canvas.tagName !== 'CANVAS') {
        throw new Error('[AnimeForge] Invalid canvas element or selector.');
      }

      /** @type {CanvasRenderingContext2D} */
      this._ctx = this._canvas.getContext('2d');

      this._sceneUrl = sceneUrl;
      this._options = options;

      // Apply dimensions
      this._canvas.width = options.width || this._canvas.clientWidth || 960;
      this._canvas.height = options.height || this._canvas.clientHeight || 540;

      // Sub-systems
      this._emitter   = new EventEmitter();
      this._layers    = new LayerManager(this);
      this._zones     = new ZoneManager(this);
      this._character = new CharacterRenderer(this);
      this._effects   = new EffectManager(this);
      this._lighting  = new LightingManager();

      // State
      this._loaded    = false;
      this._running   = false;
      this._paused    = false;
      this._lastTime  = 0;
      this._rafId     = null;
      this._time      = 'day';
      this._season    = 'summer';
      this._weather   = 'clear';
      this._autoTime  = options.autoTime ?? false;
      this._transitionDuration = options.transitionDuration ?? 2000;

      /** @type {Object|null} Raw parsed scene data */
      this._sceneData = null;

      // Auto-time tracking
      this._autoTimeInterval = null;

      // Bind the loop so we can cancel it
      this._loop = this._loop.bind(this);
    }

    // ---- Public API ---------------------------------------------------------

    /**
     * Load the scene definition and all required assets.
     * @returns {Promise<void>}
     * @fires SceneRenderer#stateChange
     * @fires SceneRenderer#load
     */
    async load() {
      this._emitter.emit('stateChange', { state: 'loading' });

      const { SceneLoader } = AnimeForge;
      if (!SceneLoader) {
        throw new Error('[AnimeForge] SceneLoader not found. Include scene-loader.js.');
      }

      const loader = new SceneLoader(this._sceneUrl);

      loader.onProgress((progress) => {
        this._emitter.emit('loadProgress', progress);
      });

      this._sceneData = await loader.load();
      this._applySceneData(this._sceneData);
      this._loaded = true;
      this._emitter.emit('stateChange', { state: 'loaded' });
      this._emitter.emit('load', this._sceneData);

      // Start render loop
      this._start();
    }

    /**
     * Set the time of day.
     * @param {string} time - 'dawn' | 'day' | 'sunset' | 'night'
     * @param {Object} [opts]
     * @param {number} [opts.duration] - Transition duration in ms.
     */
    setTime(time, opts = {}) {
      const validTimes = ['dawn', 'day', 'sunset', 'night'];
      if (!validTimes.includes(time)) {
        console.warn(`[AnimeForge] Invalid time "${time}". Use: ${validTimes.join(', ')}`);
        return;
      }
      const oldTime = this._time;
      if (time === oldTime) return;

      this._time = time;
      const duration = opts.duration ?? this._transitionDuration;
      this._layers.transitionTo(time, duration);
      this._lighting.setTime(time);
      this._emitter.emit('timeChange', time, oldTime);
      this._emitter.emit('stateChange', { state: 'timeChange', time, oldTime });
    }

    /**
     * Set the weather effect.
     * @param {string} weather - 'clear' | 'rain' | 'snow' | 'fog' | 'sun'
     */
    setWeather(weather) {
      const validWeather = ['clear', 'rain', 'snow', 'fog', 'sun', 'leaves'];
      if (!validWeather.includes(weather)) {
        console.warn(`[AnimeForge] Invalid weather "${weather}". Use: ${validWeather.join(', ')}`);
        return;
      }
      const prev = this._effects.setWeather(weather);
      this._weather = weather;
      this._emitter.emit('weatherChange', weather, prev);
      this._emitter.emit('stateChange', { state: 'weatherChange', weather });
    }

    /**
     * Set the season (affects leaf colors and potential palette shifts).
     * @param {string} season - 'spring' | 'summer' | 'fall' | 'winter'
     */
    setSeason(season) {
      const validSeasons = ['spring', 'summer', 'fall', 'winter'];
      if (!validSeasons.includes(season)) {
        console.warn(`[AnimeForge] Invalid season "${season}".`);
        return;
      }
      this._season = season;
      this._emitter.emit('seasonChange', season);
      this._emitter.emit('stateChange', { state: 'seasonChange', season });
    }

    /**
     * Play a character animation.
     * @param {string} name - Animation name.
     * @param {Object} [opts]
     * @param {number} [opts.crossfadeDuration=300]
     */
    playAnimation(name, opts = {}) {
      this._character.play(name, opts);
    }

    /**
     * Transition from one animation to another.
     * @param {string} from
     * @param {string} to
     * @param {Object} [opts]
     * @param {number} [opts.duration=500]
     */
    transition(from, to, opts = {}) {
      this._character.transition(from, to, opts);
    }

    /**
     * Set the animation for a specific zone.
     * @param {string} zoneId
     * @param {string} animationName
     */
    setZoneAnimation(zoneId, animationName) {
      this._zones.setZoneAnimation(zoneId, animationName);
    }

    /** Pause rendering and animation. */
    pause() {
      this._paused = true;
      this._emitter.emit('stateChange', { state: 'paused' });
    }

    /** Resume rendering and animation. */
    resume() {
      if (!this._paused) return;
      this._paused = false;
      this._lastTime = performance.now();
      this._emitter.emit('stateChange', { state: 'running' });
    }

    /**
     * Enable or disable automatic time-of-day based on the real clock.
     * @param {boolean} enabled
     */
    setAutoTime(enabled) {
      this._autoTime = enabled;
      if (enabled) {
        this._updateAutoTime();
        this._autoTimeInterval = setInterval(() => this._updateAutoTime(), 60000);
      } else if (this._autoTimeInterval) {
        clearInterval(this._autoTimeInterval);
        this._autoTimeInterval = null;
      }
    }

    /**
     * Subscribe to an event.
     * @param {string} event
     * @param {Function} fn
     * @returns {Function} Unsubscribe function.
     */
    on(event, fn) {
      return this._emitter.on(event, fn);
    }

    /**
     * Unsubscribe from an event.
     * @param {string} event
     * @param {Function} fn
     */
    off(event, fn) {
      this._emitter.off(event, fn);
    }

    /**
     * Get current scene state.
     * @returns {Object}
     */
    getState() {
      return {
        loaded: this._loaded,
        running: this._running,
        paused: this._paused,
        time: this._time,
        season: this._season,
        weather: this._weather,
        animation: this._character.currentAnimation,
        autoTime: this._autoTime,
        canvasWidth: this._canvas.width,
        canvasHeight: this._canvas.height,
      };
    }

    /**
     * Resize the canvas.
     * @param {number} width
     * @param {number} height
     */
    resize(width, height) {
      this._canvas.width = width;
      this._canvas.height = height;
    }

    /**
     * Destroy the renderer and clean up all resources.
     */
    destroy() {
      this._running = false;
      if (this._rafId) {
        cancelAnimationFrame(this._rafId);
        this._rafId = null;
      }
      if (this._autoTimeInterval) {
        clearInterval(this._autoTimeInterval);
        this._autoTimeInterval = null;
      }
      this._emitter.removeAll();
      this._emitter.emit('stateChange', { state: 'destroyed' });
    }

    // ---- Internal -----------------------------------------------------------

    /**
     * Apply parsed scene data to sub-systems.
     * @private
     * @param {Object} data - Loaded scene data from SceneLoader.
     */
    _applySceneData(data) {
      // --- Layers ---
      if (data.layers) {
        for (const layer of data.layers) {
          const depth = layer.depth || 'background';
          if (layer.images) {
            for (const [time, img] of Object.entries(layer.images)) {
              this._layers.addLayer(depth, time, img, layer.parallax_factor || 0);
            }
          }
        }
      }

      // --- Zones ---
      if (data.zones) {
        for (const zone of data.zones) {
          this._zones.addZone(zone.id, {
            x: zone.x,
            y: zone.y,
            width: zone.width,
            height: zone.height,
            type: zone.type,
            scale: zone.scale,
          });
        }
      }

      // --- Character animations ---
      if (data.animations) {
        for (const anim of data.animations) {
          if (anim.image) {
            this._character.addAnimation(anim.name, anim.image, {
              frameWidth: anim.frame_width,
              frameHeight: anim.frame_height,
              frameCount: anim.frame_count,
              fps: anim.fps,
              loop: anim.loop,
            });
          }
        }
      }

      // --- Set initial state ---
      const initial = data.initial || {};
      this._time = initial.time || 'day';
      this._season = initial.season || 'summer';
      this._weather = initial.weather || 'clear';

      this._layers._currentTime = this._time;
      this._layers._fadeProgress = 1;
      this._lighting.setTime(this._time);
      // Force immediate lighting (skip transition)
      this._lighting._current = [...this._lighting._target];

      if (initial.weather && initial.weather !== 'clear') {
        this._effects.setWeather(initial.weather);
      }

      // Play default animation if specified
      if (initial.animation) {
        this._character.play(initial.animation);
      }
    }

    /** @private */
    _start() {
      if (this._running) return;
      this._running = true;
      this._lastTime = performance.now();
      this._emitter.emit('stateChange', { state: 'running' });

      if (this._autoTime) {
        this.setAutoTime(true);
      }

      this._rafId = requestAnimationFrame(this._loop);
    }

    /**
     * Main render loop.
     * @private
     * @param {number} timestamp
     */
    _loop(timestamp) {
      if (!this._running) return;
      this._rafId = requestAnimationFrame(this._loop);

      if (this._paused) return;

      const dt = Math.min(timestamp - this._lastTime, 50); // cap delta to avoid spiral
      this._lastTime = timestamp;

      const ctx = this._ctx;
      const w = this._canvas.width;
      const h = this._canvas.height;

      // --- Update phase ---
      this._layers.update(dt);
      this._character.update(dt);
      this._effects.update(dt, w, h);
      this._lighting.update(dt);

      // --- Draw phase ---
      ctx.clearRect(0, 0, w, h);

      // 1. Background layers
      this._layers.draw(ctx, 'background', w, h);

      // 2. Midground layers
      this._layers.draw(ctx, 'midground', w, h);

      // 3. Character sprite in active zone
      this._drawCharacter(ctx, w, h);

      // 4. Foreground layers
      this._layers.draw(ctx, 'foreground', w, h);

      // 5. Weather / particle effects
      this._effects.draw(ctx, w, h);

      // 6. Lighting overlay
      this._lighting.draw(ctx, w, h);
    }

    /**
     * Draw the character at the appropriate zone position.
     * @private
     */
    _drawCharacter(ctx, canvasW, canvasH) {
      const zoneId = this._zones.getCharacterZoneId();
      if (!zoneId) {
        // No zone defined — draw at center-bottom as fallback
        this._character.draw(ctx, canvasW * 0.35, canvasH * 0.3);
        return;
      }

      const pos = this._zones.getZonePosition(zoneId, canvasW, canvasH);
      if (pos) {
        this._character.draw(ctx, pos.x, pos.y, pos.scale);
      }
    }

    /**
     * Determine time of day from the real clock and set it.
     * @private
     */
    _updateAutoTime() {
      const hour = new Date().getHours();
      let time;
      if (hour >= 5 && hour < 8)        time = 'dawn';
      else if (hour >= 8 && hour < 17)   time = 'day';
      else if (hour >= 17 && hour < 20)  time = 'sunset';
      else                                time = 'night';

      if (time !== this._time) {
        this.setTime(time);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Expose public API
  // ---------------------------------------------------------------------------

  if (!global.AnimeForge) {
    global.AnimeForge = {};
  }

  /**
   * Create a new AnimeForge scene.
   *
   * @example
   * const scene = new AnimeForge.Scene('#canvas', 'scene.json');
   * await scene.load();
   * scene.setTime('night');
   * scene.setWeather('rain');
   * scene.playAnimation('typing');
   * scene.on('timeChange', (newTime, oldTime) => {
   *   console.log(`Time changed: ${oldTime} -> ${newTime}`);
   * });
   */
  global.AnimeForge.Scene = SceneRenderer;

  // Expose internals for advanced use and testing
  global.AnimeForge._internals = {
    EventEmitter,
    LayerManager,
    ZoneManager,
    CharacterRenderer,
    EffectManager,
    LightingManager,
    Particle,
  };

})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
