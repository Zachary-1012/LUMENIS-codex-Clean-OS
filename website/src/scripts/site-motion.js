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
if (opticalField instanceof HTMLElement && finePointer.matches) {
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

if (finePointer.matches) {
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
    const stepByHash = new Map(links.map((link, index) => [link.hash, index]));
    stepByHash.set("#demo-source", 0);

    const writeHash = (hash) => {
      if (window.location.hash === hash) return;
      window.history.pushState({ lumenisWebsiteRoute: true }, "", hash);
    };

    const selectStep = (requestedIndex, announce = true, historyHash = null) => {
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

      if (historyHash) writeHash(historyHash);
      if (announce) liveStatus.textContent = `${label}. ${summary}`;
    };

    links.forEach((link, index) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        selectStep(index, true, link.hash);
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
        selectStep(nextIndex, true, links[nextIndex].hash);
        links[nextIndex].focus();
      });
    });

    range.addEventListener("input", () => {
      const index = Number(range.value) || 0;
      selectStep(index, true, links[index].hash);
    });

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
        selectStep(0, true, "#demo-source");
        if (sourceHeading instanceof HTMLElement) sourceHeading.focus();
      });
    });

    const restoreStepFromHash = () => {
      const index = stepByHash.get(window.location.hash);
      if (index === undefined) return;
      selectStep(index, true);
    };

    window.addEventListener("popstate", restoreStepFromHash);
    window.addEventListener("hashchange", restoreStepFromHash);
    chain.dataset.chainEnhanced = "true";
    chain.dataset.chainView = "linear";
    selectStep(stepByHash.get(window.location.hash) ?? range.value, false);
  }
}

const workflow = document.querySelector("[data-workflow-root]");
if (workflow instanceof HTMLElement) {
  const questionControls = workflow.querySelector("[data-workflow-question-controls]");
  const questions = [...workflow.querySelectorAll("[data-workflow-question]")];
  const panels = [...workflow.querySelectorAll("[data-workflow-panel]")];
  const liveStatus = workflow.querySelector("[data-workflow-status]");

  const workflows = questions.map((button) => {
    if (!(button instanceof HTMLButtonElement)) return null;
    const panel = panels.find((candidate) => candidate.dataset.workflowPanel === button.dataset.workflowQuestion);
    if (!(panel instanceof HTMLElement)) return null;

    const tabs = [...panel.querySelectorAll("[data-workflow-stage-tab]")];
    const stages = [...panel.querySelectorAll("[data-workflow-stage]")];
    const previous = panel.querySelector("[data-workflow-previous]");
    const next = panel.querySelector("[data-workflow-next]");
    const position = panel.querySelector("[data-workflow-position]");
    const returnLink = panel.querySelector("[data-workflow-return]");
    const tabList = panel.querySelector("[data-workflow-stage-controls]");
    const traversal = panel.querySelector("[data-workflow-traversal]");

    if (
      tabs.length !== 3 ||
      stages.length !== tabs.length ||
      !tabs.every((tab) => tab instanceof HTMLButtonElement) ||
      !stages.every((stage) => stage instanceof HTMLElement) ||
      !(previous instanceof HTMLButtonElement) ||
      !(next instanceof HTMLButtonElement) ||
      !(position instanceof HTMLElement) ||
      !(returnLink instanceof HTMLAnchorElement) ||
      !(tabList instanceof HTMLElement) ||
      !(traversal instanceof HTMLElement)
    ) return null;

    return { button, panel, tabs, stages, previous, next, position, returnLink, tabList, traversal };
  });

  if (
    questionControls instanceof HTMLElement &&
    liveStatus instanceof HTMLElement &&
    workflows.length === 2 &&
    workflows.length === questions.length &&
    workflows.length === panels.length &&
    workflows.every(Boolean)
  ) {
    const routeByHash = new Map();
    workflows.forEach((entry, questionIndex) => {
      routeByHash.set(`#${entry.panel.id}`, { questionIndex, stageIndex: 0 });
      entry.stages.forEach((stage, stageIndex) => {
        routeByHash.set(`#${stage.id}`, { questionIndex, stageIndex });
      });
    });

    let currentQuestionIndex = 0;
    let currentStageIndex = 0;

    const writeWorkflowHash = (hash) => {
      if (window.location.hash === hash) return;
      window.history.pushState({ lumenisWebsiteRoute: true }, "", hash);
    };

    const setSelection = (questionIndex, stageIndex, { announcement, historyHash } = {}) => {
      const entry = workflows[questionIndex];
      if (!entry) return;

      currentQuestionIndex = questionIndex;
      currentStageIndex = Math.max(0, Math.min(entry.stages.length - 1, stageIndex));
      workflows.forEach((candidate, candidateIndex) => {
        candidate.button.setAttribute("aria-controls", candidate.panel.id);
        candidate.button.setAttribute("aria-pressed", String(candidateIndex === currentQuestionIndex));
        candidate.button.tabIndex = candidateIndex === currentQuestionIndex ? 0 : -1;
        candidate.panel.hidden = candidateIndex !== currentQuestionIndex;
      });

      entry.tabs.forEach((tab, tabIndex) => {
        const stage = entry.stages[tabIndex];
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-controls", stage.id);
        tab.setAttribute("aria-selected", String(tabIndex === currentStageIndex));
        tab.tabIndex = tabIndex === currentStageIndex ? 0 : -1;
        stage.setAttribute("role", "tabpanel");
        stage.setAttribute("aria-labelledby", tab.id);
        stage.tabIndex = 0;
        stage.hidden = tabIndex !== currentStageIndex;
      });

      entry.previous.disabled = currentStageIndex === 0;
      entry.next.disabled = currentStageIndex === entry.stages.length - 1;
      entry.position.textContent = workflowPosition(currentStageIndex + 1, entry.stages.length);

      if (historyHash) writeWorkflowHash(historyHash);
      if (announcement) liveStatus.textContent = announcement;
    };

    const workflowPosition = (current, total) => {
      const template = workflow.dataset.workflowPositionPattern || "{current} / {total}";
      return template.replace("{current}", String(current)).replace("{total}", String(total));
    };

    const selectQuestion = (questionIndex, { announce = true, writeHistory = true } = {}) => {
      const entry = workflows[questionIndex];
      if (!entry) return;
      setSelection(questionIndex, 0, {
        announcement: announce ? `${workflowQuestionChanged()} ${entry.stages[0].querySelector("h4")?.textContent || ""}` : "",
        historyHash: writeHistory ? `#${entry.panel.id}` : null,
      });
    };

    const selectStage = (stageIndex, { announce = true, writeHistory = true } = {}) => {
      const entry = workflows[currentQuestionIndex];
      const stage = entry?.stages[stageIndex];
      if (!entry || !stage) return;
      setSelection(currentQuestionIndex, stageIndex, {
        announcement: announce ? `${workflowStagePrefix()} ${stage.querySelector("h4")?.textContent || ""}` : "",
        historyHash: writeHistory ? `#${stage.id}` : null,
      });
    };

    const workflowQuestionChanged = () => workflow.dataset.workflowQuestionChanged || "";
    const workflowStagePrefix = () => workflow.dataset.workflowStagePrefix || "";
    const workflowRestoredAnnouncement = () => workflow.dataset.workflowRestored || "";
    const restoreWorkflowFromHash = () => {
      const route = routeByHash.get(window.location.hash);
      if (!route) return;
      setSelection(route.questionIndex, route.stageIndex, {
        announcement: `${workflowRestoredAnnouncement()} ${workflows[route.questionIndex].stages[route.stageIndex].querySelector("h4")?.textContent || ""}`,
      });
    };

    workflows.forEach((entry, questionIndex) => {
      entry.button.addEventListener("click", () => selectQuestion(questionIndex));
      entry.button.addEventListener("keydown", (event) => {
        let nextIndex = questionIndex;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex += 1;
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex -= 1;
        else if (event.key === "Home") nextIndex = 0;
        else if (event.key === "End") nextIndex = workflows.length - 1;
        else return;

        event.preventDefault();
        nextIndex = Math.max(0, Math.min(workflows.length - 1, nextIndex));
        selectQuestion(nextIndex);
        workflows[nextIndex].button.focus();
      });

      entry.tabs.forEach((tab, stageIndex) => {
        tab.addEventListener("click", () => selectStage(stageIndex));
        tab.addEventListener("keydown", (event) => {
          let nextIndex = stageIndex;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex += 1;
          else if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex -= 1;
          else if (event.key === "Home") nextIndex = 0;
          else if (event.key === "End") nextIndex = entry.tabs.length - 1;
          else return;

          event.preventDefault();
          nextIndex = Math.max(0, Math.min(entry.tabs.length - 1, nextIndex));
          selectStage(nextIndex);
          entry.tabs[nextIndex].focus();
        });
      });

      entry.previous.addEventListener("click", () => selectStage(currentStageIndex - 1));
      entry.next.addEventListener("click", () => selectStage(currentStageIndex + 1));
      entry.returnLink.addEventListener("click", (event) => {
        event.preventDefault();
        selectQuestion(questionIndex);
        entry.button.focus();
      });
    });

    window.addEventListener("popstate", restoreWorkflowFromHash);
    window.addEventListener("hashchange", restoreWorkflowFromHash);

    const initialRoute = routeByHash.get(window.location.hash) || { questionIndex: 0, stageIndex: 0 };
    setSelection(initialRoute.questionIndex, initialRoute.stageIndex);
    workflows.forEach((entry) => {
      entry.tabList.hidden = false;
      entry.traversal.hidden = false;
      entry.returnLink.hidden = false;
    });
    questionControls.hidden = false;
    workflow.dataset.workflowEnhanced = "true";
  }
}
