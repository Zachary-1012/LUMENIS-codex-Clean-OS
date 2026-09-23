# LUMENIS public website

This package is the public acquisition surface for LUMENIS. It is a small,
static Astro site with three locale routes:

- `/` — 简体中文
- `/en/` — English
- `/ko/` — 한국어

It explains the product and its boundaries. It does not own Product Truth,
accounts, workflow execution, evidence, permissions, or any provider key.

## Local checks

```powershell
cd website
npm install
npm run build
npm test
```

`npm run build` is a preview build when no public origin is supplied. Preview
output includes `noindex,nofollow`, blocks robots, and omits canonical URLs and
`hreflang` links. A deployed build must use a verified public HTTPS origin and
reachable destinations. Set `LUMENIS_PUBLIC_SITE_ORIGIN` and, when available,
`LUMENIS_PUBLIC_TRIAL_URL`, `LUMENIS_PUBLIC_CONTACT_URL`,
`LUMENIS_PUBLIC_HELP_URL`, and `LUMENIS_PUBLIC_WORKSPACE_URL` to the actual
deployment URLs before building. Reserved example hosts such as
`example.invalid`, `example.com`, `.test`, and localhost fail the build when
supplied as public URLs.

```powershell
npm run build
```

The four destination variables are optional, public HTTPS URLs. An unset
destination remains an explicit, non-dead disabled state in the rendered page;
there is no pretend submission or client-side secret handling.

## Design and ownership

`DEVELOPMENT-BRIEF.md` records the website-scoped implementation assumptions,
the current Experience Constitution grammar, and the standards research used
for this package. It is not a competing product or design authority.
