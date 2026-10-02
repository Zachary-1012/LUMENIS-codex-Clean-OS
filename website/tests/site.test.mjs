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

test("hero and workflow explainer use localized business language", async () => {
  const workflow = {
    "index.html": {
      heroLabels: ["资料", "交付", "反馈"],
      caption: "从资料整理到业务交付，再根据反馈复盘下一步。",
      heading: "从资料走到交付，再复盘结果",
      steps: ["资料", "问题", "判断", "计划", "交付", "复盘"],
      returnLine: "根据交付后的反馈，修正下一轮计划。",
    },
    "en/index.html": {
      heroLabels: ["Material", "Delivery", "Feedback"],
      caption: "From sourced material to business delivery, then use feedback to improve the next plan.",
      heading: "From material to delivery, then review",
      steps: ["Material", "Question", "Decision", "Plan", "Delivery", "Review"],
      returnLine: "Use delivery feedback to refine the next plan.",
    },
    "ko/index.html": {
      heroLabels: ["자료", "전달", "피드백"],
      caption: "자료를 정리해 업무 결과로 전달하고, 피드백을 바탕으로 다음 계획을 다듬습니다.",
      heading: "자료에서 전달까지, 결과를 다시 살핍니다",
      steps: ["자료", "질문", "판단", "계획", "전달", "되돌아보기"],
      returnLine: "전달 결과와 피드백을 자료에 다시 대조해 다음 계획을 다듬습니다.",
    },
  };

  for (const [path, copy] of Object.entries(workflow)) {
    const html = await page(path);
    const heroLabels = [...html.matchAll(/<span class="hero-field__label[^\"]*">([^<]+)<\/span>/g)]
      .map(([, label]) => label);
    const caption = html.match(/<figcaption id="hero-visual-caption">([^<]+)<\/figcaption>/)?.[1];
    const sequence = html.match(/<section class="sequence-section"[^>]*>([\s\S]*?)<\/section>/)?.[1];

    assert.deepEqual(heroLabels, copy.heroLabels, `${path} localizes the three business labels`);
    assert.equal(caption, copy.caption, `${path} explains the flow in the figure caption`);
    assert.ok(sequence, `${path} renders the workflow explanation`);
    assert.ok(sequence.includes(copy.heading), `${path} localizes the workflow heading`);
    assert.ok(sequence.includes(copy.returnLine), `${path} localizes the feedback loop`);

    const steps = [...sequence.matchAll(/<span class="sequence-node__name">([^<]+)<\/span>/g)]
      .map(([, name]) => name);
    assert.deepEqual(steps, copy.steps, `${path} explains work from material through review`);
    assert.doesNotMatch(sequence, /\b(?:POINT|AXIS|TRACE|FIELD|STRATA|BOUNDARY)\b/);
  }
});

test("business questions keep a complete no-JavaScript, three-stage preview", async () => {
  const localizedStages = {
    "index.html": [
      "先汇集可核对的材料",
      "区分已证实与待确认事项",
      "把选择整理成团队计划",
      "汇集可追溯的市场材料",
      "比较受众、内容与合作选择",
      "整理一份带依据的 Brief",
    ],
    "en/index.html": [
      "Gather material that can be checked",
      "Separate verified resources from open questions",
      "Set out a plan the team can review",
      "Gather traceable market material",
      "Compare audience, content, and partner choices",
      "Prepare a brief with its support attached",
    ],
    "ko/index.html": [
      "확인 가능한 자료를 모읍니다",
      "확인된 자원과 미확인 사항을 나눕니다",
      "팀이 검토할 계획을 정리합니다",
      "출처를 추적할 수 있는 시장 자료를 모읍니다",
      "대상, 콘텐츠와 협업 방향을 비교합니다",
      "근거와 함께 브리프를 준비합니다",
    ],
  };
  const workflowLabels = {
    "index.html": "工作路径示意",
    "en/index.html": "Workflow path preview",
    "ko/index.html": "업무 경로 미리보기",
  };

  for (const [path, headings] of Object.entries(localizedStages)) {
    const html = await page(path);
    const stages = [...html.matchAll(/<section class="workflow-stage"([^>]*)>([\s\S]*?)<\/section>/g)];

    assert.equal((html.match(/data-workflow-question="(?:commerce|brand)"/g) ?? []).length, 2, path);
    assert.equal(stages.length, 6, `${path} lists all three stages for both questions`);
    assert.match(html, /class="workflow-question-list"[^>]*hidden/);
    assert.match(html, /class="workflow-stage-list"[^>]*hidden/);
    assert.match(html, /class="workflow-traversal"[^>]*hidden/);
    assert.doesNotMatch(stages.map(([, attributes]) => attributes).join(" "), /\shidden(?:\s|>)/);
    const labels = [...html.matchAll(/<span class="workflow-preview-label">([^<]+)<\/span>/g)].map(([, label]) => label);
    assert.deepEqual(labels, [workflowLabels[path], workflowLabels[path]], `${path} labels both paths as previews`);

    for (const heading of headings) {
      assert.ok(html.includes(heading), `${path} includes “${heading}”`);
    }
  }
});

test("hero workspace entry is configured or honestly unavailable", async () => {
  const workspace = process.env.LUMENIS_PUBLIC_WORKSPACE_URL;

  for (const path of pages) {
    const html = await page(path);
    const heroActions = html.match(/<div class="hero__actions">([\s\S]*?)<\/div>/)?.[1];
    assert.ok(heroActions, `${path} renders hero actions`);
    assert.match(heroActions, /href="#scenarios"/);

    if (workspace) {
      const expectedHref = new URL(workspace).href.replaceAll("&", "&amp;");
      assert.ok(heroActions.includes(`href="${expectedHref}"`), `${path} uses the configured workspace destination`);
      assert.doesNotMatch(heroActions, /action-link--disabled/);
    } else {
      assert.match(heroActions, /action-link--disabled[^>]*aria-disabled="true"/);
      assert.doesNotMatch(heroActions, /href="(?:https?:|\/\/|\/)/);
    }
  }
});

test("public copy avoids retired local-AI claims and states capability availability", async () => {
  const localizedCapabilityStatus = {
    "index.html": {
      retiredAiClaim: /设备本地\s*AI|本地\s*AI|本地模型|在线模型可用/,
      availability: "各表面可提供的能力取决于运行环境与部署配置。",
    },
    "en/index.html": {
      retiredAiClaim: /device-local\s*AI|local\s*AI|local model|live model availability/i,
      availability: "Available capabilities vary by surface, runtime, and deployment.",
    },
    "ko/index.html": {
      retiredAiClaim: /기기 내\s*AI|로컬\s*AI|기기 내 모델|실시간 모델 제공/,
      availability: "각 표면에서 제공하는 기능은 실행 환경과 배포 설정에 따라 다릅니다.",
    },
  };

  for (const [path, expected] of Object.entries(localizedCapabilityStatus)) {
    const html = await page(path);
    assert.doesNotMatch(html, expected.retiredAiClaim, `${path} avoids the retired local-AI claim`);
    assert.ok(html.includes(expected.availability), `${path} states that capability availability depends on its environment`);
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

test("the illustrative business chain keeps every step available without JavaScript", async () => {
  for (const path of pages) {
    const html = await page(path);
    const steps = [...html.matchAll(/class="chain-step"[^>]*href="#demo-step-([^"]+)"/g)];
    const details = [...html.matchAll(/class="demo-detail"/g)];

    assert.equal(steps.length, 9, `${path} renders all business-chain nodes`);
    assert.equal(details.length, 9, `${path} keeps all detail sections in the static document`);
    assert.match(html, /data-chain-view-toggle hidden/);
    assert.match(html, /data-chain-controls hidden/);
    assert.match(html, /aria-live="polite"/);
    assert.match(html, /aria-describedby="trace-range-help"/);
    assert.doesNotMatch(html, /class="demo-detail"[^>]*\shidden/);

    for (const [, id] of steps) {
      assert.match(html, new RegExp(`id="demo-step-${id}"`), `${path} resolves the ${id} detail`);
    }
  }
});

test("spatial browsing remains opt-in, localized, and motion-aware", async () => {
  const motion = await readFile(new URL("../src/scripts/site-motion.js", import.meta.url), "utf8");
  const styles = await readFile(new URL("../src/styles/site.css", import.meta.url), "utf8");

  for (const path of pages) {
    const html = await page(path);
    assert.match(html, /Illustration layout|示意区排列方式|예시 배치 방식/);
    assert.match(html, /Linear timeline|线性时间线|선형 타임라인/);
    assert.match(html, /Orbit view|环形探索|원형 탐색/);
  }

  assert.match(motion, /prefers-reduced-motion: reduce/);
  assert.match(motion, /pointer: fine/);
  assert.match(motion, /data-chain-view-option/);
  assert.match(motion, /ArrowRight/);
  assert.match(motion, /ArrowDown/);
  assert.match(motion, /popstate/);
  assert.match(motion, /hashchange/);
  assert.match(motion, /data-workflow-root/);
  assert.match(styles, /data-chain-view="orbit"/);
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
});

test("the public page does not expose secrets or internal operation identifiers", async () => {
  const html = await page("index.html");
  assert.doesNotMatch(html, /sk-[A-Za-z0-9]{20,}/);
  assert.doesNotMatch(html, /password|api[_-]?key|cookie|session[_-]?token/i);
  assert.doesNotMatch(html, /data-(?:evidence|permission|database|owner|api)/i);
});

test("access actions never imply a configured destination", async () => {
  const html = await page("index.html");
  const accessList = html.match(/<ul class="access-list">([\s\S]*?)<\/ul>/)?.[1] ?? "";
  const disabledActions = (accessList.match(/action-link--disabled/g) ?? []).length;
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
