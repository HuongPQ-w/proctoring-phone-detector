(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const finalCounters = () => {
    document.querySelectorAll("[data-count-to]").forEach((element) => {
      const suffix = element.dataset.countSuffix || "";
      element.textContent = `${Number(element.dataset.countTo || "0")}${suffix}`;
    });
  };

  const countUp = (element, duration = 820) => {
    const target = Number(element.dataset.countTo || "0");
    const suffix = element.dataset.countSuffix || "";
    const start = performance.now();

    element.textContent = `0${suffix}`;

    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = `${Math.round(target * eased)}${suffix}`;
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  };

  if (reduceMotion) {
    finalCounters();
    return;
  }

  const delayClass = (index) => `motion-delay-${Math.min(index, 9)}`;

  const prepare = (selector, extraClasses = []) => {
    const items = [...document.querySelectorAll(selector)];
    items.forEach((item, index) => {
      item.classList.add("motion-item", delayClass(index), ...extraClasses);
    });
    return items;
  };

  const show = (items) => {
    items.forEach((item) => item.classList.add("is-visible"));
  };

  const observe = (rootSelector, items, onShow) => {
    const root = document.querySelector(rootSelector);
    if (!root || !items.length) return;

    const reveal = () => {
      show(items);
      if (onShow) onShow();
    };

    if (!("IntersectionObserver" in window)) {
      reveal();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        reveal();
        observer.disconnect();
      },
      { threshold: 0.18, rootMargin: "0px 0px -12% 0px" }
    );

    observer.observe(root);
  };

  const header = prepare(".site-header", ["motion-from-top"]);
  const heroBackdrop = prepare(".hero-backdrop", ["motion-scale-soft", "motion-no-blur"]);
  const heroKicker = prepare(".hero-copy .kicker");
  const heroTitle = prepare(".hero-copy h1 span", ["motion-hero-line", "motion-strong-rise"]);
  const heroIntro = prepare(".hero-intro");
  const heroConsole = prepare(".hero-console", ["motion-scale-soft"]);
  const quickSources = prepare(".quick-source", ["motion-low-rise", "motion-panel-rise"]);
  const detectionFrame = prepare(".detection-frame", ["motion-scale-soft"]);
  const visionBox = prepare(".vision-box", ["motion-scale-in", "motion-no-blur"]);
  const frameStatus = prepare(".frame-status strong", ["motion-low-rise", "motion-no-blur"]);

  const proof = prepare(".proof-section .section-label, .proof-section .proof-media, .proof-section .proof-copy h2, .proof-section .proof-steps article", ["motion-panel-rise"]);
  const source = prepare(".source-section .section-heading > *, .source-section .collection-card", ["motion-panel-rise"]);
  const alert = prepare(".alert-section .section-heading > *, .alert-section .alert-card", ["motion-panel-rise"]);
  const faq = prepare(".faq-section .section-heading > *, .faq-section .faq-item", ["motion-panel-rise"]);
  const finalCta = prepare(".final-cta .final-cta-content > *");
  const finalImage = prepare(".final-cta img", ["motion-image-in", "motion-no-blur"]);
  const footer = prepare(".site-footer .brand, .site-footer p, .site-footer .footer-links", ["motion-low-rise"]);
  const signalItems = prepare(".signal-demo > *", ["motion-low-rise", "motion-panel-rise"]);

  document.documentElement.classList.add("motion-ready");

  requestAnimationFrame(() => {
    window.setTimeout(() => show(header), 0);
    window.setTimeout(() => show(heroBackdrop), 60);
    window.setTimeout(() => show(heroKicker), 140);
    window.setTimeout(() => show(heroTitle), 220);
    window.setTimeout(() => show(heroIntro), 460);
    window.setTimeout(() => show(heroConsole), 580);
    window.setTimeout(() => show(quickSources), 700);
    window.setTimeout(() => show(detectionFrame), 420);
    window.setTimeout(() => show(visionBox), 960);
    window.setTimeout(() => show(frameStatus), 1050);
  });

  observe(".proof-section", proof);
  observe(".source-section", source);
  observe(".alert-section", alert);
  observe(".faq-section", faq);
  observe(".final-cta", [...finalImage, ...finalCta]);
  observe(".site-footer", footer);

  const dashboard = document.querySelector("[data-dashboard]");
  if (dashboard) {
    observe("[data-dashboard]", signalItems, () => {
      dashboard.querySelector(".signal-chart")?.classList.add("is-visible");
      dashboard.querySelectorAll("[data-count-to]").forEach((element) => countUp(element));
    });
  }
})();
