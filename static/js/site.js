(() => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (window.localIcons) {
    window.localIcons.createIcons();
  } else if (window.lucide) {
    window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  }

  const initCanvasCursor = () => {
    const canvas = document.getElementById("canvas");
    const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    if (!canvas || prefersReducedMotion || coarsePointer) {
      if (canvas) canvas.remove();
      return;
    }

    const ctx = canvas.getContext("2d", { alpha: true });
    const pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let lines = [];
    let frameId = 0;

    const config = {
      friction: 0.5,
      trails: 20,
      size: 50,
      dampening: 0.25,
      tension: 0.98,
    };

    class Oscillator {
      constructor(options = {}) {
        this.phase = options.phase || 0;
        this.offset = options.offset || 0;
        this.frequency = options.frequency || 0.001;
        this.amplitude = options.amplitude || 1;
        this.current = this.offset;
      }

      update() {
        this.phase += this.frequency;
        this.current = this.offset + Math.sin(this.phase) * this.amplitude;
        return this.current;
      }
    }

    class Node {
      constructor() {
        this.x = pos.x;
        this.y = pos.y;
        this.vx = 0;
        this.vy = 0;
      }
    }

    class Line {
      constructor(options = {}) {
        this.spring = options.spring + 0.1 * Math.random() - 0.02;
        this.friction = config.friction + 0.01 * Math.random() - 0.002;
        this.nodes = Array.from({ length: config.size }, () => new Node());
      }

      update() {
        let spring = this.spring;
        let node = this.nodes[0];
        node.vx += (pos.x - node.x) * spring;
        node.vy += (pos.y - node.y) * spring;

        for (let index = 0; index < this.nodes.length; index += 1) {
          node = this.nodes[index];
          if (index > 0) {
            const previous = this.nodes[index - 1];
            node.vx += (previous.x - node.x) * spring;
            node.vy += (previous.y - node.y) * spring;
            node.vx += previous.vx * config.dampening;
            node.vy += previous.vy * config.dampening;
          }

          node.vx *= this.friction;
          node.vy *= this.friction;
          node.x += node.vx;
          node.y += node.vy;
          spring *= config.tension;
        }
      }

      draw() {
        let x = this.nodes[0].x;
        let y = this.nodes[0].y;
        ctx.beginPath();
        ctx.moveTo(x, y);

        for (let index = 1; index < this.nodes.length - 2; index += 1) {
          const current = this.nodes[index];
          const next = this.nodes[index + 1];
          x = 0.5 * (current.x + next.x);
          y = 0.5 * (current.y + next.y);
          ctx.quadraticCurveTo(current.x, current.y, x, y);
        }

        const beforeLast = this.nodes[this.nodes.length - 2];
        const last = this.nodes[this.nodes.length - 1];
        ctx.quadraticCurveTo(beforeLast.x, beforeLast.y, last.x, last.y);
        ctx.stroke();
        ctx.closePath();
      }
    }

    const hue = new Oscillator({
      phase: Math.random() * 2 * Math.PI,
      amplitude: 18,
      frequency: 0.0012,
      offset: 78,
    });

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(window.innerWidth * dpr);
      canvas.height = Math.floor(window.innerHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const createLines = () => {
      lines = [];
      for (let index = 0; index < config.trails; index += 1) {
        lines.push(new Line({ spring: 0.4 + (index / config.trails) * 0.025 }));
      }
    };

    const move = (event) => {
      if (event.touches && event.touches.length > 0) {
        pos.x = event.touches[0].clientX;
        pos.y = event.touches[0].clientY;
        return;
      }
      pos.x = event.clientX;
      pos.y = event.clientY;
    };

    const render = () => {
      ctx.globalCompositeOperation = "source-over";
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      ctx.globalCompositeOperation = "lighter";
      ctx.strokeStyle = `hsla(${Math.round(hue.update())}, 48%, 68%, 0.18)`;
      ctx.lineWidth = 1.15;

      for (let index = 0; index < lines.length; index += 1) {
        lines[index].update();
        lines[index].draw();
      }

      frameId = window.requestAnimationFrame(render);
    };

    resizeCanvas();
    createLines();

    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("mousemove", move, { passive: true });
    window.addEventListener("touchmove", move, { passive: true });
    window.addEventListener("touchstart", move, { passive: true });
    frameId = window.requestAnimationFrame(render);

    window.addEventListener("beforeunload", () => {
      window.cancelAnimationFrame(frameId);
    });
  };

  initCanvasCursor();

  const header = document.querySelector(".site-header");
  if (header) {
    let ticking = false;
    const syncHeader = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 18);
      ticking = false;
    };
    const requestSync = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(syncHeader);
    };
    syncHeader();
    window.addEventListener("scroll", requestSync, { passive: true });
  }

  document.querySelectorAll("[data-file-input]").forEach((input) => {
    const meta = document.querySelector(`[data-file-meta="${input.id}"]`);
    const dropzone = input.closest("[data-dropzone]");
    const updateMeta = () => {
      if (!meta) return;
      const file = input.files && input.files[0];
      if (!file) {
        meta.innerHTML = "<span>Chưa chọn file</span><small>Chọn file để chuẩn bị phân tích.</small>";
        return;
      }
      const sizeMb = file.size / (1024 * 1024);
      meta.innerHTML = `<span>${file.name}</span><small>${sizeMb.toFixed(sizeMb >= 10 ? 1 : 2)} MB</small>`;
    };

    input.addEventListener("change", updateMeta);

    if (dropzone) {
      ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
          event.preventDefault();
          dropzone.classList.add("is-dragging");
        });
      });
      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("is-dragging");
      });
      dropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragging");
        if (event.dataTransfer?.files?.length) {
          input.files = event.dataTransfer.files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
      dropzone.addEventListener("dragend", () => {
          dropzone.classList.remove("is-dragging");
      });
    }
  });

  const faqTriggers = document.querySelectorAll(".faq-trigger");
  faqTriggers.forEach((trigger) => {
    const item = trigger.closest(".faq-item");
    const panel = document.getElementById(trigger.getAttribute("aria-controls"));
    if (!item || !panel) return;

    const setPanel = (open) => {
      item.classList.toggle("is-open", open);
      trigger.setAttribute("aria-expanded", String(open));
      panel.setAttribute("aria-hidden", String(!open));
    };

    trigger.addEventListener("click", () => {
      const isOpen = item.classList.contains("is-open");
      document.querySelectorAll(".faq-item.is-open").forEach((openItem) => {
        if (openItem === item) return;
        const openTrigger = openItem.querySelector(".faq-trigger");
        const openPanel = document.getElementById(openTrigger?.getAttribute("aria-controls"));
        if (!openTrigger || !openPanel) return;
        openItem.classList.remove("is-open");
        openTrigger.setAttribute("aria-expanded", "false");
        openPanel.setAttribute("aria-hidden", "true");
      });
      setPanel(!isOpen);
    });
  });

  const toggle = document.querySelector("[data-nav-toggle]");
  const menu = document.querySelector("[data-nav-menu]");
  if (!toggle || !menu) return;

  const closeMenu = () => {
    menu.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  };

  toggle.addEventListener("click", () => {
    const open = menu.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  document.addEventListener("click", (event) => {
    if (!menu.classList.contains("is-open")) return;
    if (menu.contains(event.target) || toggle.contains(event.target)) return;
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
})();
