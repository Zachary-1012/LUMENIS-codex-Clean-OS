# Browser QA attempt, 2026-10-17 12:41 UTC

Authorized scope: official cloud browser, independent local review preview only, no product service or deployment.

- `cua.getState()` succeeded: cloud Chrome inventory contained a new-tab page. No existing account/support tabs were changed.
- Static server command was scoped to `review_working`, bound only to `127.0.0.1:8766`.
- Official `cua.createBrowserTab('cdp','http://127.0.0.1:8766/#commands')` created/reported tab 5 but returned `net::ERR_CONNECTION_REFUSED`. No review page loaded.
- A subsequent shell request to the same loopback address also failed with connection-refused. The initial non-TTY execution session reported running but no server log. A normal TTY launch explicitly printed `Serving HTTP on 127.0.0.1 port 8766`, yet a later shell request still failed. The subsequent process list did not show the server.
- Both execution sessions were ended with Ctrl-C (exit 1 and 130). No listener was exposed on another interface, no local browser process was launched, and no proxy or external hosting was used.

The exact cause of cross-call service reachability is unverified. These results do not establish a browser policy denial or browser incapability. Browser focus, modal, storage, navigation and file-cancellation acceptance remains PENDING. Node and minimal-DOM evidence are separately recorded and cannot replace it.

## Normal file-URL check, 12:43 UTC
The existing fully embedded visual companion HTML was tried once through the same official cloud browser, solely to check document reachability. The browser URL security policy rejected `file:` and stated only `http:`/`https:` protocols are allowed. That action stopped immediately; no protocol encoding, proxy, security-setting change or alternative route was used. This does not validate the modular interactive demo. No further file-URL attempt is authorized by this report.
