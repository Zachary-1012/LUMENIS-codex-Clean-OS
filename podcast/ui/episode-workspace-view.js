import { buildEpisodeWorkspace, EPISODE_WORKSPACE } from './episode-workspace-model-v1.js';

/**
 * Framework-neutral DOM renderer for the first interactive workspace.
 * Host applications provide player.seek(ms) and openDrawer(payload).
 */
export function renderEpisodeWorkspace(root, episode, { player, openDrawer } = {}) {
  if (!root) throw new Error('workspace root is required');
  const view = buildEpisodeWorkspace(episode);
  root.replaceChildren();

  const title = document.createElement('h1');
  title.textContent = view.title;
  root.append(title);

  const nav = document.createElement('nav');
  EPISODE_WORKSPACE.primary.forEach((section) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = section;
    button.addEventListener('click', () => root.querySelector(`#episode-${section}`)?.scrollIntoView({ behavior: 'smooth' }));
    nav.append(button);
  });
  root.append(nav);

  const runtime = document.createElement('section');
  runtime.id = 'episode-runtime';
  runtime.append(sectionHeading('Runtime'));
  for (const segment of episode.segments ?? []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = `${formatMs(segment.start_ms)} · ${segment.kind}`;
    button.addEventListener('click', () => player?.seek?.(segment.start_ms));
    runtime.append(button);
  }
  root.append(runtime);

  const evidence = document.createElement('section');
  evidence.id = 'episode-evidence';
  evidence.append(sectionHeading('Evidence'));
  for (const item of episode.evidence ?? []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = item.title ?? item.id;
    button.addEventListener('click', () => openDrawer?.({ type: 'evidence', item }));
    evidence.append(button);
  }
  root.append(evidence);

  return view;
}

function sectionHeading(label) {
  const heading = document.createElement('h2');
  heading.textContent = label;
  return heading;
}

function formatMs(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}
