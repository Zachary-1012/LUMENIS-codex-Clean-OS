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

  return parsed.href;
}

export const publicDestinations = Object.freeze({
  trial: readPublicUrl("LUMENIS_PUBLIC_TRIAL_URL"),
  contact: readPublicUrl("LUMENIS_PUBLIC_CONTACT_URL"),
  help: readPublicUrl("LUMENIS_PUBLIC_HELP_URL"),
  workspace: readPublicUrl("LUMENIS_PUBLIC_WORKSPACE_URL"),
});
