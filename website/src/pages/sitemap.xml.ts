import type { APIRoute } from "astro";
import { publicFamilies, localPath } from '../public-content';

export const prerender = true;

const locales = ["zh-CN", "en", "ko"] as const;
const families = ['', ...publicFamilies];

export const GET: APIRoute = ({ site }) => {
  if (!site) {
    return new Response("Sitemap is unavailable until LUMENIS_PUBLIC_SITE_ORIGIN is configured.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  const urls = families.flatMap((family) => locales.map((language) => {
    const path = localPath(language, family);
    const loc = new URL(path, site).href;
    const alternates = locales
      .map((locale) => `    <xhtml:link rel="alternate" hreflang="${locale}" href="${new URL(localPath(locale, family), site).href}" />`)
      .join("\n");
    return `  <url>\n    <loc>${loc}</loc>\n${alternates}\n    <xhtml:link rel="alternate" hreflang="x-default" href="${new URL(localPath('zh-CN', family), site).href}" />\n  </url>`;
  }));

  return new Response(
    [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
      ...urls,
      "</urlset>",
      "",
    ].join("\n"),
    { headers: { "Content-Type": "application/xml; charset=utf-8" } },
  );
};
