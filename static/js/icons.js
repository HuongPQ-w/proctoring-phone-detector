(() => {
  const iconNodes = {
    "aperture": [
      ["circle", { cx: 12, cy: 12, r: 9 }],
      ["path", { d: "M14.3 3.3 10 10.8" }],
      ["path", { d: "M20.7 14.3h-8.6" }],
      ["path", { d: "M9.7 20.7 14 13.2" }],
      ["path", { d: "M3.3 9.7h8.6" }],
      ["path", { d: "M14.3 20.7 10 13.2" }],
      ["path", { d: "M9.7 3.3 14 10.8" }],
    ],
    "arrow-up-right": [
      ["path", { d: "M7 17 17 7" }],
      ["path", { d: "M8 7h9v9" }],
    ],
    "chevron-down": [["path", { d: "m6 9 6 6 6-6" }]],
    "circle-alert": [
      ["circle", { cx: 12, cy: 12, r: 9 }],
      ["path", { d: "M12 8v5" }],
      ["path", { d: "M12 16h.01" }],
    ],
    "circle-dot-dashed": [
      ["path", { d: "M10.1 2.2a10 10 0 0 1 3.8 0" }],
      ["path", { d: "M17.8 4.6a10 10 0 0 1 2 3.3" }],
      ["path", { d: "M21.8 10.1a10 10 0 0 1 0 3.8" }],
      ["path", { d: "M19.4 17.8a10 10 0 0 1-3.3 2" }],
      ["path", { d: "M13.9 21.8a10 10 0 0 1-3.8 0" }],
      ["path", { d: "M6.2 19.4a10 10 0 0 1-2-3.3" }],
      ["path", { d: "M2.2 13.9a10 10 0 0 1 0-3.8" }],
      ["path", { d: "M4.6 6.2a10 10 0 0 1 3.3-2" }],
      ["circle", { cx: 12, cy: 12, r: 2 }],
    ],
    "file-video": [
      ["path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }],
      ["path", { d: "M14 2v6h6" }],
      ["path", { d: "m10 14 4-2.5V16z" }],
      ["rect", { x: 7, y: 11, width: 10, height: 6, rx: 1 }],
    ],
    "film": [
      ["rect", { x: 3, y: 4, width: 18, height: 16, rx: 2 }],
      ["path", { d: "M7 4v16" }],
      ["path", { d: "M17 4v16" }],
      ["path", { d: "M3 8h4" }],
      ["path", { d: "M17 8h4" }],
      ["path", { d: "M3 16h4" }],
      ["path", { d: "M17 16h4" }],
    ],
    "focus": [
      ["path", { d: "M4 8V5a1 1 0 0 1 1-1h3" }],
      ["path", { d: "M16 4h3a1 1 0 0 1 1 1v3" }],
      ["path", { d: "M20 16v3a1 1 0 0 1-1 1h-3" }],
      ["path", { d: "M8 20H5a1 1 0 0 1-1-1v-3" }],
      ["circle", { cx: 12, cy: 12, r: 3 }],
    ],
    "image": [
      ["rect", { x: 3, y: 5, width: 18, height: 14, rx: 2 }],
      ["circle", { cx: 8.5, cy: 10, r: 1.5 }],
      ["path", { d: "m21 15-5-5L5 19" }],
    ],
    "image-up": [
      ["rect", { x: 3, y: 5, width: 18, height: 14, rx: 2 }],
      ["path", { d: "m21 15-5-5L5 19" }],
      ["path", { d: "M12 13V7" }],
      ["path", { d: "m9 10 3-3 3 3" }],
    ],
    "menu": [
      ["path", { d: "M4 7h16" }],
      ["path", { d: "M4 12h16" }],
      ["path", { d: "M4 17h16" }],
    ],
    "play": [["path", { d: "M7 4v16l13-8z" }]],
    "radio": [
      ["path", { d: "M4.9 19.1a10 10 0 0 1 0-14.2" }],
      ["path", { d: "M7.8 16.2a6 6 0 0 1 0-8.5" }],
      ["circle", { cx: 12, cy: 12, r: 2 }],
      ["path", { d: "M16.2 7.8a6 6 0 0 1 0 8.5" }],
      ["path", { d: "M19.1 4.9a10 10 0 0 1 0 14.2" }],
    ],
    "refresh-cw": [
      ["path", { d: "M21 12a9 9 0 0 1-15.5 6.2" }],
      ["path", { d: "M3 12A9 9 0 0 1 18.5 5.8" }],
      ["path", { d: "M18 2v4h4" }],
      ["path", { d: "M6 22v-4H2" }],
    ],
    "scan-line": [
      ["path", { d: "M4 7V5a1 1 0 0 1 1-1h2" }],
      ["path", { d: "M17 4h2a1 1 0 0 1 1 1v2" }],
      ["path", { d: "M20 17v2a1 1 0 0 1-1 1h-2" }],
      ["path", { d: "M7 20H5a1 1 0 0 1-1-1v-2" }],
      ["path", { d: "M7 12h10" }],
    ],
    "shield-check": [
      ["path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" }],
      ["path", { d: "m9 12 2 2 4-5" }],
    ],
    "siren": [
      ["path", { d: "M7 18v-6a5 5 0 0 1 10 0v6" }],
      ["path", { d: "M5 18h14" }],
      ["path", { d: "M12 2v2" }],
      ["path", { d: "m4.2 4.2 1.4 1.4" }],
      ["path", { d: "m18.4 5.6 1.4-1.4" }],
      ["path", { d: "M8 22h8" }],
    ],
    "sliders-horizontal": [
      ["path", { d: "M21 6h-7" }],
      ["path", { d: "M10 6H3" }],
      ["circle", { cx: 12, cy: 6, r: 2 }],
      ["path", { d: "M21 18h-7" }],
      ["path", { d: "M10 18H3" }],
      ["circle", { cx: 12, cy: 18, r: 2 }],
      ["path", { d: "M21 12h-3" }],
      ["path", { d: "M14 12H3" }],
      ["circle", { cx: 16, cy: 12, r: 2 }],
    ],
    "video": [
      ["path", { d: "M15 10.5 21 7v10l-6-3.5" }],
      ["rect", { x: 3, y: 6, width: 12, height: 12, rx: 2 }],
    ],
  };

  const createNode = (documentRef, node) => {
    const [tag, attrs] = node;
    const element = documentRef.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  };

  const createIcons = () => {
    document.querySelectorAll("[data-lucide]").forEach((placeholder) => {
      const name = placeholder.getAttribute("data-lucide");
      const nodes = iconNodes[name] || iconNodes.circle-alert;
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "currentColor");
      svg.setAttribute("stroke-width", "1.8");
      svg.setAttribute("stroke-linecap", "round");
      svg.setAttribute("stroke-linejoin", "round");
      svg.setAttribute("aria-hidden", placeholder.getAttribute("aria-hidden") || "true");
      svg.setAttribute("focusable", "false");
      svg.dataset.lucide = name;
      nodes.forEach((node) => svg.appendChild(createNode(document, node)));
      placeholder.replaceWith(svg);
    });
  };

  window.localIcons = { createIcons };
})();
