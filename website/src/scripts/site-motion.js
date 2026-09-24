const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

reduceMotion.addEventListener("change", (event) => {
  if (!event.matches) return;

  document.querySelectorAll("[data-optical-field]").forEach((field) => {
    if (!(field instanceof HTMLElement)) return;
    field.style.removeProperty("--pointer-x");
    field.style.removeProperty("--pointer-y");
    field.style.removeProperty("--tilt-x");
    field.style.removeProperty("--tilt-y");
    field.classList.remove("has-pointer");
  });
  document.querySelectorAll("[data-magnetic]").forEach((target) => {
    if (!(target instanceof HTMLElement)) return;
    target.style.removeProperty("--magnet-x");
    target.style.removeProperty("--magnet-y");
  });
});

const opticalField = document.querySelector("[data-optical-field]");
if (opticalField instanceof HTMLElement && finePointer.matches && !reduceMotion.matches) {
  opticalField.addEventListener("pointermove", (event) => {
    if (event.pointerType !== "mouse" || reduceMotion.matches) return;

    const bounds = opticalField.getBoundingClientRect();
    const x = event.clientX - bounds.left;
    const y = event.clientY - bounds.top;
    const horizontal = (x / bounds.width) * 2 - 1;
    const vertical = (y / bounds.height) * 2 - 1;

    opticalField.style.setProperty("--pointer-x", `${x}px`);
    opticalField.style.setProperty("--pointer-y", `${y}px`);
    opticalField.style.setProperty("--tilt-x", `${horizontal * 3}deg`);
    opticalField.style.setProperty("--tilt-y", `${vertical * -3}deg`);
    opticalField.classList.add("has-pointer");
  });

  opticalField.addEventListener("pointerleave", () => {
    opticalField.style.removeProperty("--tilt-x");
    opticalField.style.removeProperty("--tilt-y");
    opticalField.classList.remove("has-pointer");
  });
}

if (finePointer.matches && !reduceMotion.matches) {
  document.querySelectorAll("[data-magnetic]").forEach((target) => {
    if (!(target instanceof HTMLElement)) return;

    target.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse" || reduceMotion.matches) return;

      const bounds = target.getBoundingClientRect();
      const offsetX = (event.clientX - (bounds.left + bounds.width / 2)) / bounds.width;
      const offsetY = (event.clientY - (bounds.top + bounds.height / 2)) / bounds.height;
      target.style.setProperty("--magnet-x", `${Math.max(-5, Math.min(5, offsetX * 10))}px`);
      target.style.setProperty("--magnet-y", `${Math.max(-4, Math.min(4, offsetY * 8))}px`);
    });

    target.addEventListener("pointerleave", () => {
      target.style.removeProperty("--magnet-x");
      target.style.removeProperty("--magnet-y");
    });
  });
}

const chain = document.querySelector("[data-chain-root]");
if (chain instanceof HTMLElement) {
  const links = [...chain.querySelectorAll("[data-chain-step]")];
  const panels = [...chain.querySelectorAll("[data-chain-panel]")];
  const range = chain.querySelector("[data-chain-range]");
  const output = chain.querySelector("[data-chain-output]");
  const liveStatus = chain.querySelector("[data-chain-status]");
  const sourceHeading = chain.querySelector("[data-chain-source-heading]");
  const centerLabel = chain.querySelector("[data-chain-center]");
  const viewToggle = chain.querySelector("[data-chain-view-toggle]");
  const controls = chain.querySelector("[data-chain-controls]");
  const viewOptions = [...chain.querySelectorAll("[data-chain-view-option]")];

  if (
    links.length > 0 &&
    panels.length === links.length &&
    range instanceof HTMLInputElement &&
    output instanceof HTMLOutputElement &&
    liveStatus instanceof HTMLElement
  ) {
    const selectStep = (requestedIndex, announce = true) => {
      const index = Math.max(0, Math.min(links.length - 1, Number(requestedIndex) || 0));
      const activeLink = links[index];
      const activePanel = panels[index];
      const label = activeLink.dataset.label || activeLink.textContent.trim();
      const summary = activeLink.dataset.summary || label;

      range.value = String(index);
      range.setAttribute("aria-valuetext", label);
      output.textContent = label;
      if (centerLabel instanceof HTMLElement) centerLabel.textContent = label;
      links.forEach((link, linkIndex) => {
        if (linkIndex === index) link.setAttribute("aria-current", "step");
        else link.removeAttribute("aria-current");
      });
      panels.forEach((panel, panelIndex) => {
        panel.hidden = panelIndex !== index;
      });
      chain.style.setProperty("--chain-progress", `${(index / Math.max(1, links.length - 1)) * 100}%`);
      chain.dataset.currentStep = String(index);

      if (announce) liveStatus.textContent = `${label}. ${summary}`;
    };

    links.forEach((link, index) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        selectStep(index);
      });

      link.addEventListener("keydown", (event) => {
        let nextIndex = index;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex += 1;
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex -= 1;
        else if (event.key === "Home") nextIndex = 0;
        else if (event.key === "End") nextIndex = links.length - 1;
        else return;

        event.preventDefault();
        nextIndex = Math.max(0, Math.min(links.length - 1, nextIndex));
        selectStep(nextIndex);
        links[nextIndex].focus();
      });
    });

    range.addEventListener("input", () => selectStep(range.value));

    if (viewToggle instanceof HTMLElement && controls instanceof HTMLElement && viewOptions.length === 2) {
      viewOptions.forEach((option) => {
        if (!(option instanceof HTMLButtonElement)) return;

        option.addEventListener("click", () => {
          const view = option.dataset.chainViewOption === "orbit" ? "orbit" : "linear";
          chain.dataset.chainView = view;
          viewOptions.forEach((candidate) => {
            candidate.setAttribute("aria-pressed", String(candidate === option));
          });
          liveStatus.textContent = option.textContent.trim();
        });
      });
      viewToggle.hidden = false;
      controls.hidden = false;
    }

    chain.querySelectorAll("[data-chain-return]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        selectStep(0);
        if (sourceHeading instanceof HTMLElement) sourceHeading.focus();
      });
    });

    chain.dataset.chainEnhanced = "true";
    chain.dataset.chainView = "linear";
    selectStep(range.value, false);
  }
}
