import { defineConfig } from "astro/config";

const siteOrigin = process.env.LUMENIS_PUBLIC_SITE_ORIGIN;

function validateSiteOrigin(value) {
  if (!value) return undefined;

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error("LUMENIS_PUBLIC_SITE_ORIGIN must be a valid HTTPS origin.");
  }

  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(
      "LUMENIS_PUBLIC_SITE_ORIGIN must be an HTTPS origin without a path, credentials, query, or fragment.",
    );
  }

  return parsed.origin;
}

export default defineConfig({
  site: validateSiteOrigin(siteOrigin),
  output: "static",
  i18n: {
    locales: ["zh-CN", "en", "ko"],
    defaultLocale: "zh-CN",
  },
});
