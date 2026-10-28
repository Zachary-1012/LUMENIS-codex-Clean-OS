import { isReservedPublicHost } from "./public-host.mjs";

function readPublicUrl(name) {
  const value = process.env[name];
  if (!value) return undefined;

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be an absolute HTTPS URL.`);
  }

  if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
    throw new Error(`${name} must be an HTTPS URL without embedded credentials.`);
  }

  if (isReservedPublicHost(parsed.hostname)) {
    throw new Error(`${name} must use a real public host, not a reserved example host.`);
  }

  return parsed.href;
}

export const publicDestinations = Object.freeze({
  trial: readPublicUrl("LUMENIS_PUBLIC_TRIAL_URL"),
  contact: readPublicUrl("LUMENIS_PUBLIC_CONTACT_URL"),
  help: readPublicUrl("LUMENIS_PUBLIC_HELP_URL"),
  workspace: readPublicUrl("LUMENIS_PUBLIC_WORKSPACE_URL"),
});

// Only existing product routes may be linked from the public explanation.
// No configured destination means no guessed deployment or local-machine URL.
export function workspaceHref(screen, entry) {
  if (!publicDestinations.workspace) return undefined;
  return buildWorkspaceHref(publicDestinations.workspace, screen, entry);
}

export function buildWorkspaceHref(base, screen, entry) {
  if (!['ACC-03', 'CTH-01', 'BMP-01', 'SH-01', 'SH-02', 'SYS-05', 'SYS-08'].includes(screen)) {
    throw new Error('Unsupported public workspace destination.');
  }
  if (entry && (screen !== 'SH-01' || !['manuscript', 'video', 'audio'].includes(entry))) {
    throw new Error('Unsupported public creation destination.');
  }
  const url = new URL(base);
  const mount = url.pathname.match(/^(.*?)\/workspace(?:\/|$)/);
  const prefix = mount ? mount[1] : url.pathname.replace(/\/$/, '');
  url.pathname = `${prefix}/workspace/${screen}`;
  url.search = '';
  url.hash = '';
  if (entry) url.searchParams.set('entry', entry);
  return url.href;
}
