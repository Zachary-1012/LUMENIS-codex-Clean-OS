import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { join } from "node:path";
import { isReservedPublicHost } from "../src/public-host.mjs";

const root = new URL("../dist/", import.meta.url);
const pages = ["index.html", "en/index.html", "ko/index.html"];
const configured = Boolean(process.env.LUMENIS_PUBLIC_SITE_ORIGIN);

async function page(path) {
  return readFile(new URL(path, root), "utf8");
}

function attribute(html, name) {
  return html.match(new RegExp(`<meta[^>]+name=["']${name}["'][^>]+content=["']([^"']+)["']`, "i"))?.[1];
}

test("renders every locale as a semantic, localized document", async () => {
  for (const path of pages) {
    const html = await page(path);
    assert.match(html, /<html lang="(?:zh-CN|en|ko)">/);
    assert.match(html, /<header[\s>]/);
    assert.match(html, /<nav[\s>]/);
    assert.match(html, /<main id="main">/);
    assert.match(html, /<footer[\s>]/);
    assert.match(html, /<h1[\s>]/);
    assert.match(html, /<h2[\s>]/);
    assert.match(html, /application\/ld\+json/);
    assert.match(html, /Illustrative|Fictional|허구|虚构/);
  }
});

test("preview output is closed to search indexing until an origin is configured", async () => {
  const html = await page("index.html");
  const robots = await readFile(new URL("robots.txt", root), "utf8");
  const sitemap = await readFile(new URL("sitemap.xml", root), "utf8");

  if (configured) {
    assert.equal(attribute(html, "robots"), "index,follow");
    assert.match(html, /rel="canonical"/);
    assert.match(html, /hreflang="en"/);
    assert.match(robots, /Allow: \/\nSitemap:/);
    assert.match(sitemap, /<urlset[\s>]/);
    assert.match(sitemap, /hreflang="x-default"/);
  } else {
    assert.equal(attribute(html, "robots"), "noindex,nofollow");
    assert.doesNotMatch(html, /rel="canonical"/);
    assert.doesNotMatch(html, /hreflang=/);
    assert.match(robots, /Disallow: \/\n/);
    assert.match(sitemap, /unavailable/i);
  }
});

test("internal actions resolve to known anchors or localized routes", async () => {
  for (const path of pages) {
    const html = await page(path);
    const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]));
    const hrefs = [...html.matchAll(/\shref="([^"]+)"/g)].map((match) => match[1]);

    for (const href of hrefs.filter((value) => value.startsWith("#"))) {
      assert.ok(ids.has(href.slice(1)), `${path} points to missing anchor ${href}`);
    }

    assert.ok(hrefs.includes("/"));
    assert.ok(hrefs.includes("/en/"));
    assert.ok(hrefs.includes("/ko/"));
  }
});

test("the public page does not expose secrets or internal operation identifiers", async () => {
  const html = await page("index.html");
  assert.doesNotMatch(html, /sk-[A-Za-z0-9]{20,}/);
  assert.doesNotMatch(html, /password|api[_-]?key|cookie|session[_-]?token/i);
  assert.doesNotMatch(html, /data-(?:evidence|permission|database|owner|api)/i);
});

test("access actions never imply a configured destination", async () => {
  const html = await page("index.html");
  const disabledActions = (html.match(/text-link--disabled/g) ?? []).length;
  const destinationVariables = [
    "LUMENIS_PUBLIC_TRIAL_URL",
    "LUMENIS_PUBLIC_CONTACT_URL",
    "LUMENIS_PUBLIC_HELP_URL",
    "LUMENIS_PUBLIC_WORKSPACE_URL",
  ];
  const configuredDestinations = destinationVariables.filter((name) => process.env[name]);

  assert.equal(disabledActions, 4 - configuredDestinations.length);
  for (const name of configuredDestinations) {
    const url = new URL(process.env[name]);
    assert.ok(html.includes(`href="${url.href.replaceAll("&", "&amp;")}"`));
  }
});

test("reserved example hosts cannot stand in for public destinations", () => {
  for (const host of [
    "example.invalid",
    "public.example.invalid",
    "example.com",
    "workspace.example.com",
    "localhost",
    "app.localhost",
    "sample.test",
  ]) {
    assert.equal(isReservedPublicHost(host), true, host);
  }
  assert.equal(isReservedPublicHost("lumenis.example-business.cn"), false);
});
