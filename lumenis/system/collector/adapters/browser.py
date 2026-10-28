"""Anonymous rendered documents through the existing SYSTEM Browser runtime.

This is a bounded Source transport, not a browser/session manager. Every network
request is fulfilled through the existing pinned public HTTP transport; personal
profiles, CDP, browser Cookies and request headers are never imported. Native
continuations are reached through visible read controls, never replayed as tasks.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
import sys
from urllib.parse import urlsplit

import requests

from .public_source import (
    PublicResponse, PublicSourceError, PublicSourceHTTPError,
    PublicSourceHTTPAdapter, _validate_allowed_https_host,
    _validate_public_url_and_pin, fetch_public_url,
)


@dataclass(frozen=True)
class PublicBrowserDocument:
    document: PublicResponse
    originals: tuple[PublicResponse, ...]
    native_pages: tuple[dict, ...]
    extraction: dict
    steps: int
    cursor_reached: bool


class PublicBrowserVerificationRequired(PublicSourceError):
    failure_type = "PUBLIC_BROWSER_VERIFICATION"


def select_public_transport(platform, options, *, configured=None, use_server=True):
    """Resolve transport before the first attempt; never choose on failure."""
    value = options.get("public_transport")
    if value is None and use_server:
        from config import get_config
        value = get_config().get(f"LUMENIS_{platform.upper()}_PUBLIC_TRANSPORT")
    value = value or configured or "http"
    if value not in {"http", "browser"}:
        raise PublicSourceError("public transport must be explicitly http or browser")
    return value


def read_public_document(url, originals, *, transport="http", fetcher=None,
                         browser_plan=None, **kwargs):
    if transport == "http":
        response = (fetcher or fetch_public_url)(url, **kwargs)
        originals.append(response)
        return response, None
    if transport != "browser":
        raise PublicSourceError("public transport is invalid")
    observed = fetch_public_browser(url, **kwargs, **(browser_plan or {}))
    originals.extend(observed.originals)
    return observed.document, observed


def _native_post(url, body, *, allowed_host_suffixes, timeout, max_bytes):
    """Only a browser-emitted, allowlisted native read reaches this function."""
    _validate_allowed_https_host(url, allowed_host_suffixes)
    trace = []
    checked, pins = _validate_public_url_and_pin(url, resolution_trace=trace)
    if not isinstance(body, str) or len(body.encode("utf-8")) > 256_000:
        raise PublicSourceError("native public read body exceeds its bound")
    try:
        decoded = json.loads(body)
    except (ValueError, TypeError):
        raise PublicSourceError("native public read body must be JSON") from None
    # YouTube's anonymous page emits these read-only commands. No social write,
    # auth mutation, age/consent override or other POST command is admitted.
    if (not isinstance(decoded, dict) or not decoded
            or set(decoded) - {"context", "continuation", "videoId", "browseId", "params"}):
        raise PublicSourceError("native public read command is not allowed")
    with requests.Session() as client:
        client.mount("https://", PublicSourceHTTPAdapter(host_pins=pins))
        try:
            response = client.post(checked, data=body.encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                auth=lambda request: request, timeout=(min(timeout, 5), min(timeout, 15)),
                allow_redirects=False, stream=True, verify=True)
            try:
                if not 200 <= response.status_code < 300:
                    raise PublicSourceHTTPError(response.status_code, requested_url=url,
                        final_url=url, resolution_trace=trace)
                size, chunks = 0, []
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise PublicSourceError("native public read response exceeds its bound")
                    chunks.append(chunk)
                return PublicResponse(url, b"".join(chunks),
                    str(response.headers.get("Content-Type") or "application/json").split(";", 1)[0],
                    response.status_code, requested_url=url, resolution_trace=tuple(trace))
            finally:
                response.close()
        except requests.RequestException:
            raise PublicSourceError("native public read transport failed") from None


def fetch_public_browser(url, *, allowed_host_suffixes, asset_host_suffixes=(),
                         capture_paths=(), request_keys=(), read_controls=(),
                         extraction_script=None, cursor=None, max_steps=2,
                         read_action_script=None,
                         timeout=20, max_bytes=8_000_000, cancel_check=None,
                         browser_factory=None):
    """Read one public page with a fresh anonymous SYSTEM Browser context.

    Scripts/selectors are adapter-owned constants, never task-provided code.
    ``cursor`` contains only a previously observed native path/request tuple;
    it selects an observed response after visible navigation, not an HTTP replay.
    Returned rendered DOM is marked separately from actual transport originals.
    No caller can supply a Cookie, browser profile, CDP URL or storage state.
    """
    from lumenis.adapters.human_browser import NativeReadCapture
    from lumenis.system.browser.runtime.adapters.playwright_adapter import PlaywrightAdapter

    suffixes = tuple(allowed_host_suffixes)
    assets = tuple(dict.fromkeys((*suffixes, *asset_host_suffixes)))
    if type(max_steps) is not int or not 0 <= max_steps <= 40:
        raise PublicSourceError("public browser step bound is invalid")
    if cursor is not None and (not isinstance(cursor, dict)
            or not isinstance(cursor.get("path"), str) or not isinstance(cursor.get("request"), dict)
            or not cursor["request"]
            or set(cursor["request"]) - set(request_keys)
            or not any(re.fullmatch(pattern, cursor["path"]) for pattern in capture_paths)):
        raise PublicSourceError("public browser native cursor is invalid")
    _validate_allowed_https_host(url, suffixes)
    _validate_public_url_and_pin(url)
    originals, failures, used, requests_seen = [], [], 0, 0
    redirected = {}
    deadline = time.monotonic() + min(max(float(timeout), 1), 60) + max_steps * 1.0
    launch_options = {"headless": True, "timeout_ms": min(int(timeout * 1000), 30_000)}
    if sys.platform == "win32":
        # Select the installed Edge channel before any source attempt. It is
        # launched in a new context; the user's Edge profile is never opened.
        from cdp_helper import _registered_edge_executable
        if _registered_edge_executable() is None:
            raise PublicSourceError("the selected installed Edge public browser is unavailable")
        launch_options["channel"] = "msedge"
    browser = (browser_factory or PlaywrightAdapter)(**launch_options)
    page = getattr(browser, "_page", None)
    context = getattr(browser, "_context", None)
    if page is None or context is None:
        browser.close()
        raise PublicSourceError("SYSTEM public browser runtime is unavailable")
    # BrowserContext routing cannot intercept service-worker-controlled traffic.
    # Reuse this runtime's launched browser, replacing only its still-empty
    # anonymous context with the documented service_workers='block' variant.
    try:
        if any(getattr(browser, field, None) for field in ("cdp_url", "user_data_dir", "storage_state")):
            raise PublicSourceError("public browser requires a fresh anonymous context")
        context.close()
        context = browser._browser.new_context(service_workers="block", accept_downloads=False)
        page = context.new_page()
        page.set_default_timeout(min(int(timeout * 1000), 30_000))
        browser._context, browser._page = context, page
        context.route_web_socket("**/*", lambda route: route.close())
    except Exception:
        browser.close()
        raise PublicSourceError("SYSTEM public browser isolation is unavailable") from None
    native = NativeReadCapture(hosts=(), paths=(), request_keys=request_keys)
    # Route observations are recorded after the existing public transport has
    # checked DNS/TLS/redirects. No raw browser request or header leaves here.
    native.pages = []

    def check():
        if time.monotonic() > deadline:
            raise PublicSourceError("public browser read deadline exceeded")
        if callable(cancel_check) and cancel_check():
            raise PublicSourceError("public browser read cancelled")
        if failures:
            raise failures[0]

    def route_read(route, request):
        nonlocal used, requests_seen
        try:
            check()
            requests_seen += 1
            if requests_seen > 128:
                raise PublicSourceError("public browser request bound exceeded")
            parsed = urlsplit(request.url)
            resource = request.resource_type
            main = resource == "document"
            read = resource in {"xhr", "fetch"} and parsed.hostname in {urlsplit(url).hostname} and any(
                re.fullmatch(pattern, parsed.path) for pattern in capture_paths)
            if request.method not in {"GET", "POST"} or request.method == "POST" and not read:
                route.abort("blockedbyclient")
                return
            if resource not in {"document", "script", "stylesheet", "font", "image", "xhr", "fetch"} or resource in {"xhr", "fetch"} and not read:
                route.abort("blockedbyclient")
                return
            allowed = suffixes if main or read else assets
            _validate_allowed_https_host(request.url, allowed)
            _validate_public_url_and_pin(request.url)
            if request.method == "POST":
                # Only these source-emitted anonymous YouTube read APIs are
                # currently proven read-only; other platforms use GET/DOM.
                if parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com"} or parsed.path not in {
                        "/youtubei/v1/search", "/youtubei/v1/browse", "/youtubei/v1/next"}:
                    route.abort("blockedbyclient")
                    return
                response = _native_post(request.url, request.post_data,
                    allowed_host_suffixes=allowed, timeout=timeout, max_bytes=max_bytes)
            else:
                response = redirected.pop(request.url, None) or fetch_public_url(request.url,
                    timeout=timeout, max_bytes=max_bytes, allowed_host_suffixes=allowed)
            if response.url != request.url:
                # Let the actual browser URL follow the already validated
                # source redirect. Do not disguise redirected content at the
                # original address or fetch the same response a second time.
                redirected[response.url] = response
                route.fulfill(status=302, headers={"location": response.url}, body=b"")
                return
            used += len(response.content)
            if used > 48_000_000:
                raise PublicSourceError("public browser aggregate response bound exceeded")
            if main or read:
                originals.append(response)
            if read:
                fields = {}
                from urllib.parse import parse_qs
                fields.update({key: values[-1] for key, values in parse_qs(parsed.query).items() if key in request_keys and values})
                if request.method == "POST":
                    decoded = json.loads(request.post_data)
                    fields.update({key: value for key, value in decoded.items() if key in request_keys})
                fields = {key: value for key, value in fields.items() if type(value) in {int, bool}
                    or isinstance(value, str) and len(value) <= 4096 and not any(ord(x) < 32 for x in value)}
                native.pages.append({"path": parsed.path, "request": fields,
                    "http_status": response.status_code, "objects": NativeReadCapture._objects(response.content.decode("utf-8", errors="replace")),
                    "failure_class": None})
            route.fulfill(status=response.status_code, body=response.content,
                headers={"content-type": response.content_type})
        except PublicSourceError as exc:
            if request.resource_type in {"document", "xhr", "fetch"}:
                failures.append(exc)
            route.abort("blockedbyclient")
        except Exception:
            failures.append(PublicSourceError("public browser source read failed"))
            route.abort("blockedbyclient")

    def wall():
        state = browser.evaluate("""() => ({title:document.title || '', text:(document.body?.innerText || '').slice(0,6000),
          verify:!!document.querySelector('#captcha,#captcha-internal,#challenge-form,iframe[src*=recaptcha],iframe[src*=hcaptcha],form[action*=checkpoint],form[action*=wappass]')})""")
        if state.get("verify") or re.search(r"^(?:just a moment|access denied|log in|sign in|security verification)|before you continue to youtube|百度安全验证|请完成验证", state.get("title", ""), re.I):
            raise PublicBrowserVerificationRequired("public browser login or verification required")
        if re.search(r"blocked by network security|whoa there, pardner|you.ve been blocked|sign in to confirm you.re not a bot", state.get("text", ""), re.I):
            raise PublicSourceHTTPError(403, requested_url=url)

    try:
        context.route("**/*", route_read)
        context.on("page", lambda popup: popup.close() if popup != page else None)
        browser.navigate(url)
        check()
        _validate_allowed_https_host(page.url, suffixes)
        wall()
        reached = cursor is None
        steps = 0
        for steps in range(max_steps + 1):
            check()
            wall()
            if cursor is not None:
                reached = any(observation["path"] == cursor["path"] and all(
                    observation["request"].get(key) == value for key, value in cursor["request"].items())
                    for observation in native.pages)
                if reached:
                    break
            elif steps >= max_steps:
                break
            if steps == max_steps:
                break
            advanced = False
            if read_action_script:
                advanced = browser.evaluate(read_action_script) is True
            for selector in read_controls:
                if advanced:
                    break
                control = page.locator(selector).first
                if control.count() and control.is_visible():
                    control.click(timeout=3000)
                    advanced = True
                    break
            if not advanced:
                page.mouse.wheel(0, 800)
            page.wait_for_timeout(700)
        check()
        wall()
        if not reached:
            raise PublicSourceError("public browser native cursor was not reached within the read bound")
        content = browser.evaluate("() => document.documentElement.outerHTML")
        if not isinstance(content, str) or len(content.encode("utf-8")) > max_bytes:
            raise PublicSourceError("public browser DOM exceeds its bound")
        extraction = browser.evaluate(extraction_script) if extraction_script else {}
        if not isinstance(extraction, dict):
            raise PublicSourceError("public browser extraction shape changed")
        _validate_allowed_https_host(page.url, suffixes)
        first = next((value for value in originals if value.content_type in {"text/html", "application/xhtml+xml"}), None)
        if first is None:
            raise PublicSourceError("public browser original document was not observed")
        document = PublicResponse(page.url, content.encode("utf-8"), "text/html", first.status_code,
            requested_url=url, redirect_chain=first.redirect_chain, resolution_trace=first.resolution_trace)
        return PublicBrowserDocument(document, tuple(originals), tuple(native.pages), extraction, steps, reached)
    except PublicSourceError:
        raise
    except Exception:
        if failures:
            raise failures[0]
        raise PublicSourceError("SYSTEM public browser read failed") from None
    finally:
        browser.close()
