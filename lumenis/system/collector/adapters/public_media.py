"""Bounded yt-dlp library adapter inside the existing public Source owner.

No CLI/configuration, browser identity, plugins, JS runtime, updater, external
downloader or model is run. SourceUse, task attempts, storage reservation and
Artifact custody remain with the caller. Every HTTP read uses public_source.
"""
from __future__ import annotations

import hashlib
import io
from itertools import islice
import json
import os
import re
import tempfile
import threading
import time
from types import FunctionType
from pathlib import Path
from urllib.parse import urlsplit

from .public_source import PublicMediaResponse, PublicResponse, PublicSourceError

YT_DLP_VERSION = "2026.10.21"
_INIT_LOCK = threading.Lock()
_EXTRACTOR_HOSTS = {
    "Generic": None, "Youtube": ("youtube.com", "youtu.be"),
    "Vimeo": ("vimeo.com",), "BiliBili": ("bilibili.com", "b23.tv"),
    "Twitter": ("x.com", "twitter.com"), "Instagram": ("instagram.com",),
    "Facebook": ("facebook.com", "fb.watch"),
}
_FORMAT_KEYS = ("format_id", "url", "protocol", "ext", "width", "height", "fps", "filesize",
                "filesize_approx", "vcodec", "acodec", "tbr", "abr", "language", "has_drm",
                "manifest_url", "fragment_base_url", "fragments")


class PublicMediaError(PublicSourceError):
    """A typed unavailable outcome, never permission to try another backend."""


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _https(value):
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.port not in (None, 443)):
            raise ValueError
    except (TypeError, ValueError):
        raise PublicMediaError("PUBLIC_MEDIA_HTTPS_SOURCE_REQUIRED") from None
    return value


def _check_document(raw, content_type):
    # These checks reject protection; they do not solve or remove it. Parsers,
    # format selection and segment assembly are supplied by the pinned library.
    if content_type in {"text/html", "application/xhtml+xml"}:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
        if (soup.select_one("#captcha, #challenge-form, .verify-page, [data-sitekey]")
                or title in {"sign in", "log in", "login", "access denied", "just a moment...", "安全验证", "访问验证"}):
            raise PublicMediaError("PUBLIC_MEDIA_ACCESS_VERIFICATION_REQUIRED")
    text = raw.decode("utf-8", "ignore")
    if (re.search(r"(?im)^#EXT-X-(?:SESSION-)?KEY:.*METHOD=(?!NONE(?:,|\s|$))", text)
            or re.search(r"<(?:[\w.-]+:)?ContentProtection(?:\s|>)", text, re.I)):
        raise PublicMediaError("PUBLIC_MEDIA_ENCRYPTED_OR_DRM_NOT_ALLOWED")


class _Quiet:
    def debug(self, *args, **kwargs):
        pass
    info = warning = error = debug


class _PublicReads:
    def __init__(self, *, captured=None, check_continue=None, max_requests=16,
                 max_bytes=32 * 1024 * 1024, binary_root=None):
        self.captured, self.callback = captured, check_continue
        self.max_requests, self.max_bytes = max_requests, max_bytes
        self.binary_root = binary_root
        self.requests, self.bytes, self.components = 0, 0, []
        self.deadline = time.monotonic() + 120
        self.first_document_sha256 = hashlib.sha256(captured.content).hexdigest() if captured else None

    def check(self):
        if self.callback:
            self.callback()
        if time.monotonic() > self.deadline:
            raise PublicMediaError("PUBLIC_MEDIA_STEP_TIME_BUDGET")

    def urlopen(self, request):
        from yt_dlp.networking.common import Response
        from .public_source import fetch_public_media, fetch_public_url
        self.check()
        url = _https(request if isinstance(request, str) else request.url)
        if not isinstance(request, str):
            if (request.method not in {"GET", "HEAD"} or request.data is not None
                    or any(key.lower() in {"authorization", "cookie", "proxy-authorization", "range"}
                           for key in request.headers)
                    or request.extensions.get("impersonate")):
                raise PublicMediaError("PUBLIC_MEDIA_REQUEST_BOUNDARY_REJECTED")
        # A HEAD requested by an extractor is fulfilled by the same bounded GET;
        # no raw urllib/Requests path, Cookie, custom proxy or alternate client.
        if self.captured and url in {self.captured.url, self.captured.requested_url}:
            response, raw = self.captured, self.captured.content
            _check_document(raw, response.content_type)
            return Response(io.BytesIO(raw), response.url,
                {"Content-Type": response.content_type, "Content-Length": str(len(raw))}, response.status_code)
        if self.requests >= self.max_requests or self.bytes >= self.max_bytes:
            raise PublicMediaError("PUBLIC_MEDIA_REQUEST_OR_BYTE_BUDGET")
        self.requests += 1
        remaining = self.max_bytes - self.bytes
        if self.binary_root is None:
            response = fetch_public_url(url, timeout=15, max_bytes=min(2 * 1024 * 1024, remaining),
                                        check_continue=self.check)
            raw = response.content
            _check_document(raw, response.content_type)
            handle = io.BytesIO(raw)
            size, digest = len(raw), hashlib.sha256(raw).hexdigest()
        else:
            path = self.binary_root / ("component-" + str(self.requests))
            response = fetch_public_media(url, destination=path, max_bytes=remaining, check_continue=self.check)
            size, digest = response.size_bytes, response.sha256
            if response.content_type in {"text/html", "application/xhtml+xml"} or urlsplit(url).path.lower().endswith((".m3u8", ".mpd")):
                if size > 2 * 1024 * 1024:
                    raise PublicMediaError("PUBLIC_MEDIA_DOCUMENT_TOO_LARGE")
                _check_document(path.read_bytes(), response.content_type)
            _retain_component(path,response,self.check)
            handle = path.open("rb")
        self.bytes += size
        if self.first_document_sha256 is None:
            self.first_document_sha256 = digest
        self.components.append({"url": response.url, "requested_url": url, "sha256": digest,
            "size_bytes": size, "content_type": response.content_type,
            "original_bytes_saved": self.binary_root is not None})
        return Response(handle, response.url,
            {"Content-Type": response.content_type, "Content-Length": str(size)}, response.status_code)


def _library(reads):
    from importlib.metadata import version
    if version("yt-dlp") != YT_DLP_VERSION:
        raise PublicMediaError("PUBLIC_MEDIA_EXTRACTOR_VERSION_UNVERIFIED")
    import yt_dlp
    from yt_dlp import globals as state
    from yt_dlp.cookies import YoutubeDLCookieJar
    class EmptyCookies(YoutubeDLCookieJar):
        def set_cookie(self, *args, **kwargs):
            raise PublicMediaError("PUBLIC_MEDIA_COOKIE_REQUIRED_NOT_ADMITTED")
    class PublicYoutubeDL(yt_dlp.YoutubeDL):
        def urlopen(self, request):
            return reads.urlopen(request)
        @property
        def cookiejar(self):
            return self.__dict__.setdefault("_public_empty_cookiejar", EmptyCookies())
    with _INIT_LOCK:
        # yt-dlp's Python constructor otherwise discovers user plugin paths.
        # This is the sole product binding; no user CLI/global config is edited.
        if state.plugin_ies.value or state.plugin_pps.value:
            raise PublicMediaError("PUBLIC_MEDIA_EXTERNAL_PLUGIN_NOT_ADMITTED")
        state.plugin_dirs.value = []
        state.all_plugins_loaded.value = True
        ydl = PublicYoutubeDL({"quiet": True, "no_warnings": True, "logger": _Quiet(),
            "cachedir": False, "cookiefile": None, "cookiesfrombrowser": None,
            "usenetrc": False, "username": None, "password": None, "videopassword": None,
            "js_runtimes": {}, "remote_components": set(), "geo_bypass": False,
            "allow_unplayable_formats": False, "skip_download": True, "noplaylist": True,
            "extractor_retries": 0, "retries": 0, "fragment_retries": 0,
            "concurrent_fragment_downloads": 1, "skip_unavailable_fragments": False,
            "external_downloader": {}, "postprocessors": [], "fixup": "never",
            "nopart": True, "continuedl": False, "overwrites": False}, auto_init=False)
        from yt_dlp.extractor import get_info_extractor
        # GenericIE delegates ordinary HTML5 parsing to this upstream embed
        # extractor. Register only that parser and known initial embed chains,
        # rather than discovering every installed/native/plugin extractor.
        for key in ("HTML5MediaEmbed","Youtube","Vimeo","BiliBili"):
            ydl.add_info_extractor(get_info_extractor(key)(ydl))
    return ydl


def _extract(ydl, url, key):
    from yt_dlp.extractor import get_info_extractor
    _https(url)
    if key not in _EXTRACTOR_HOSTS:
        raise PublicMediaError("PUBLIC_MEDIA_EXTRACTOR_NOT_ADMITTED")
    host, suffixes = urlsplit(url).hostname, _EXTRACTOR_HOSTS[key]
    if suffixes and not any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
        raise PublicMediaError("PUBLIC_MEDIA_EXTRACTOR_SOURCE_MISMATCH")
    extractor = get_info_extractor(key)(ydl)
    return extractor.extract(url)


def extract_public_media(source_url, *, captured_response=None, extractor_key="Generic",
                         check_continue=None, max_requests=16):
    """Read public metadata; no media bytes are claimed by a format plan."""
    if (type(max_requests) is not int or not 1 <= max_requests <= 32
            or captured_response is not None and (type(captured_response) is not PublicResponse
                or captured_response.status_code != 200 or len(captured_response.content) > 2 * 1024 * 1024)):
        raise PublicMediaError("PUBLIC_MEDIA_EXTRACTION_INPUT_INVALID")
    _https(source_url)
    if captured_response and source_url not in {captured_response.url, captured_response.requested_url}:
        raise PublicMediaError("PUBLIC_MEDIA_CAPTURE_BINDING_CHANGED")
    reads = _PublicReads(captured=captured_response,check_continue=check_continue,max_requests=max_requests)
    formats, chain = [], [extractor_key]
    try:
        with _library(reads) as ydl:
            info = _extract(ydl, source_url, extractor_key)
            entries = list(islice(info.get("entries") or [],129)) if info.get("_type") == "playlist" else [info]
            if len(entries) > 128:
                raise PublicMediaError("PUBLIC_MEDIA_ENTRY_BUDGET")
            for entry_index, entry in enumerate(entries):
                reads.check()
                if not isinstance(entry, dict):
                    continue
                if entry.get("_type") in {"url", "url_transparent"}:
                    key = entry.get("ie_key")
                    if key not in _EXTRACTOR_HOSTS or key == "Generic":
                        continue
                    # An observed known embed is an explicit initial chain,
                    # never a switch attempted after a refusal or challenge.
                    entry = _extract(ydl, entry["url"], key)
                    chain.append(key)
                if entry.get("is_live") or entry.get("live_status") in {"is_live", "is_upcoming"}:
                    raise PublicMediaError("PUBLIC_MEDIA_LIVE_STREAM_NOT_ADMITTED")
                candidates = entry.get("formats") or ([entry] if entry.get("url") else [])
                for index, native in enumerate(candidates):
                    if len(formats) >= 256:
                        raise PublicMediaError("PUBLIC_MEDIA_FORMAT_BUDGET")
                    if native.get("has_drm"):
                        continue
                    _https(native.get("url"))
                    value = {key: native[key] for key in _FORMAT_KEYS if key in native}
                    if value.get("protocol") is None:
                        value["protocol"] = "https"
                    if isinstance(value.get("fragments"), list) and len(value["fragments"]) > 4096:
                        raise PublicMediaError("PUBLIC_MEDIA_FRAGMENT_BUDGET")
                    value.update(entry_id=entry.get("id"), duration=entry.get("duration"),
                        native_locator={"entry_index": entry_index, "format_index": index},
                        has_drm=native.get("has_drm"), bytes_state="NOT_ACQUIRED",
                        drm_state="CLEAR_DECLARED" if native.get("has_drm") is False else "NOT_DECLARED",
                        has_video=(native["vcodec"] != "none") if native.get("vcodec") is not None else None,
                        has_audio=(native["acodec"] != "none") if native.get("acodec") is not None else None)
                    value["selection_id"] = _digest(value)
                    formats.append(value)
    except PermissionError:
        raise
    except PublicSourceError:
        raise
    except Exception as exc:
        # No raw upstream message/URL/config leaks into task diagnostics.
        raise PublicMediaError("PUBLIC_MEDIA_EXTRACTION_UNAVAILABLE") from exc
    plan = {"schema": "lumenis.public-media-plan/v1", "source_url": source_url,
        "source_document_sha256": reads.first_document_sha256,
        "extractor": {"name": "yt-dlp", "version": YT_DLP_VERSION, "key": extractor_key, "chain": chain},
        "formats": formats, "request_count": reads.requests, "network_attempted": bool(reads.requests),
        "components": reads.components, "coverage": "EXPOSED_PUBLIC_FORMATS_ONLY",
        "semantic_understanding": "NOT_RUN", "rights_state": "UNREVIEWED"}
    if len(json.dumps(plan).encode()) > 2 * 1024 * 1024:
        raise PublicMediaError("PUBLIC_MEDIA_PLAN_SIZE_BUDGET")
    return {**plan, "plan_sha256": _digest(plan)}


def fetch_extracted_public_media(plan, *, selection_id=None, selection_ids=None, destination, max_bytes,
                                 check_continue=None, allow_segment_assembly=False):
    """Acquire one selected public representation; SourceUse is caller-owned."""
    from .public_source import fetch_public_media, public_source_provenance
    if (not isinstance(plan, dict) or plan.get("schema") != "lumenis.public-media-plan/v1"
            or plan.get("extractor", {}).get("version") != YT_DLP_VERSION
            or plan.get("plan_sha256") != _digest({key:value for key,value in plan.items() if key != "plan_sha256"})):
        raise PublicMediaError("PUBLIC_MEDIA_PLAN_BINDING_CHANGED")
    if selection_ids is not None:
        if (selection_id is not None or not isinstance(selection_ids, list) or len(selection_ids) != 2
                or len(set(selection_ids)) != 2):
            raise PublicMediaError("PUBLIC_MEDIA_SELECTION_INVALID")
        return _download_tracks(plan,selection_ids,destination=destination,max_bytes=max_bytes,
            check_continue=check_continue,allow_segment_assembly=allow_segment_assembly)
    matches = [item for item in plan["formats"] if item.get("selection_id") == selection_id]
    if len(matches) != 1 or matches[0].get("has_drm") is True:
        raise PublicMediaError("PUBLIC_MEDIA_SELECTION_INVALID")
    selected = matches[0]
    if selected["protocol"] in {"https", "http"}:
        response = fetch_public_media(_https(selected["url"]), destination=destination,
                                      max_bytes=max_bytes, check_continue=check_continue)
        extraction = {"plan_sha256": plan["plan_sha256"], "selection_id": selection_id,
            "representation": "NATIVE_FILE_BYTES", "coverage": "SELECTED_FORMAT_COMPLETE",
            "components": [{"sha256": response.sha256, "size_bytes": response.size_bytes,
                            **public_source_provenance(response, selected["url"])}],
            "vcodec": selected.get("vcodec"), "acodec": selected.get("acodec")}
        return PublicMediaResponse(**{**response.__dict__, "extraction": extraction})
    if allow_segment_assembly is not True or selected["protocol"] not in {"m3u8_native", "http_dash_segments"}:
        raise PublicMediaError("PUBLIC_MEDIA_REPRESENTATION_NOT_ADMITTED")
    return _download_segments(plan, selected, destination=destination, max_bytes=max_bytes,
                              check_continue=check_continue)


def _download_segments(plan, selected, *, destination, max_bytes, check_continue):
    from .public_source import MAX_MEDIA_RESPONSE_BYTES, fetch_public_url
    from yt_dlp.downloader.hls import HlsFD
    from yt_dlp.downloader.dash import DashSegmentsFD
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists() or type(max_bytes) is not int
            or not 0 < max_bytes <= MAX_MEDIA_RESPONSE_BYTES
            or any(p.is_symlink() or getattr(p,"is_junction",lambda:False)() for p in (destination,*destination.parents))):
        raise PublicMediaError("PUBLIC_MEDIA_DESTINATION_INVALID")
    with tempfile.TemporaryDirectory(prefix="public-media-library-",dir=destination.parent) as directory:
        reads = _PublicReads(check_continue=check_continue,max_requests=4096,max_bytes=max_bytes,binary_root=Path(directory))
        info = {**selected, "id": selected.get("entry_id") or "public-media", "title": "Public source media",
                "extractor_key": plan["extractor"]["key"]}
        if selected["protocol"] == "m3u8_native":
            response = fetch_public_url(_https(selected["url"]),check_continue=reads.check)
            _check_document(response.content,response.content_type)
            manifest = response.content.decode("utf-8")
            if "#EXT-X-ENDLIST" not in manifest or not HlsFD.can_download(manifest,info):
                raise PublicMediaError("PUBLIC_MEDIA_VOD_NATIVE_ASSEMBLY_UNAVAILABLE")
            info["hls_media_playlist_data"] = manifest
            reads.requests += 1
            reads.bytes += len(response.content)
            manifest_path = Path(directory)/'manifest.original'
            manifest_path.write_bytes(response.content)
            manifest_response = PublicMediaResponse(response.url,hashlib.sha256(response.content).hexdigest(),
                len(response.content),response.content_type,response.status_code,response.requested_url)
            _retain_component(manifest_path,manifest_response,reads.check)
            reads.components.append({"url":response.url,"sha256":hashlib.sha256(response.content).hexdigest(),
                "size_bytes":len(response.content),"content_type":response.content_type,"original_bytes_saved":True})
        with _library(reads) as ydl:
            base = HlsFD if selected["protocol"] == "m3u8_native" else DashSegmentsFD
            # Reuse the pinned native downloader body, replacing only its two
            # optional external-delegation seams in a private function globals
            # mapping. No shared-library monkeypatch or PATH process discovery.
            class NoExternal:
                @staticmethod
                def available(*args, **kwargs):
                    return False
                def __init__(self,*args,**kwargs):
                    raise PublicMediaError("PUBLIC_MEDIA_EXTERNAL_DOWNLOADER_NOT_ADMITTED")
            original = base.real_download
            native = FunctionType(original.__code__,{**original.__globals__,"FFmpegFD":NoExternal,
                "get_suitable_downloader":lambda *args,**kwargs:None},original.__name__,original.__defaults__,original.__closure__)
            native_class = type('PublicNative'+base.__name__,(base,),{'real_download':native})
            downloader = native_class(ydl,ydl.params)
            output = Path(directory)/"assembled.media"
            created = False
            try:
                success, _ = downloader.download(str(output),info)
                reads.check()
                if not success or not output.is_file() or not 0 < output.stat().st_size <= max_bytes:
                    raise PublicMediaError("PUBLIC_MEDIA_ASSEMBLY_INCOMPLETE")
                digest = hashlib.sha256()
                with output.open("rb") as raw, destination.open("xb") as target:
                    created = True
                    for chunk in iter(lambda:raw.read(1024*1024),b""):
                        reads.check()
                        digest.update(chunk)
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                header = destination.open("rb")
                with header:
                    magic = header.read(400)
                mime = ("video/mp2t" if len(magic)>188 and magic[0] == magic[188] == 0x47 else
                        "audio/mp4" if selected.get("vcodec") == "none" else "video/mp4")
                return PublicMediaResponse(selected["url"],digest.hexdigest(),destination.stat().st_size,mime,200,
                    plan["source_url"],extraction={"plan_sha256":plan["plan_sha256"],"selection_id":selected["selection_id"],
                        "representation":"SEGMENTED_STREAM_ASSEMBLY","components":reads.components,
                        "coverage":"SELECTED_FORMAT_COMPONENTS_ONLY_NO_AV_MERGE",
                        "vcodec":selected.get("vcodec"),"acodec":selected.get("acodec")})
            except BaseException:
                if created:
                    destination.unlink(missing_ok=True)
                raise


def _file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def _retain_component(path, response, check_continue):
    import shared_artifacts
    with path.open("rb") as handle:
        shared_artifacts._store_content_original(handle,sha256=response.sha256,
            size_bytes=response.size_bytes,check_continue=check_continue)
    return {"sha256":response.sha256,"size_bytes":response.size_bytes,"content_type":response.content_type,
            "source_url":response.url,"original_bytes_saved":True,"extraction":response.extraction}


def _download_tracks(plan, selections, *, destination, max_bytes, check_continue, allow_segment_assembly):
    """Keep both native tracks, then copy-mux through the existing FFmpeg owner."""
    import shared_artifacts
    from lumenis.shared.content_creation.rendering import _run
    from lumenis.shared.content_creation.video_editing import _probe_media_info, MEDIA_INPUT_DEMUXERS
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists() or type(max_bytes) is not int
            or not 0 < max_bytes <= 500*1024*1024
            or any(p.is_symlink() or getattr(p,"is_junction",lambda:False)() for p in (destination,*destination.parents))):
        raise PublicMediaError("PUBLIC_MEDIA_DESTINATION_INVALID")
    values = [next((f for f in plan["formats"] if f["selection_id"] == selection),None) for selection in selections]
    if (any(value is None for value in values) or values[0].get("entry_id") != values[1].get("entry_id")
            or not values[0].get("entry_id")
            or values[0].get("native_locator",{}).get("entry_index") != values[1].get("native_locator",{}).get("entry_index")):
        raise PublicMediaError("PUBLIC_MEDIA_TRACK_IDENTITY_MISMATCH")
    ffmpeg = shared_artifacts._ffmpeg_path()
    if not ffmpeg:
        raise PublicMediaError("PUBLIC_MEDIA_MUXER_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="public-media-tracks-",dir=destination.parent) as directory:
        root, retained, paths, probes, total = Path(directory), [], [], [], 0
        for index, selection in enumerate(selections):
            path = root/('native-'+str(index)+'.media')
            response = fetch_extracted_public_media(plan,selection_id=selection,destination=path,
                max_bytes=max_bytes-total,check_continue=check_continue,allow_segment_assembly=allow_segment_assembly)
            total += response.size_bytes
            retained.append(_retain_component(path,response,check_continue))
            paths.append(path)
            probes.append(_probe_media_info(path))
        video = [i for i,p in enumerate(probes) if p.has_video]
        audio = [i for i,p in enumerate(probes) if p.audio_stream_count and not p.has_video]
        if len(video) != 1 or len(audio) != 1:
            raise PublicMediaError("PUBLIC_MEDIA_DISTINCT_VIDEO_AUDIO_TRACKS_REQUIRED")
        output = root/'copy-mux.mp4'
        command = [ffmpeg,'-v','error','-nostdin','-n','-copyts','-start_at_zero']
        for index in (video[0],audio[0]):
            command += ['-protocol_whitelist','file','-format_whitelist',MEDIA_INPUT_DEMUXERS,'-i',str(paths[index])]
        command += ['-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','-1',
                    '-fs',str(max_bytes+1),'-movflags','+faststart',str(output)]
        _run(command,cwd=root,timeout=120,check_continue=check_continue)
        probe = _probe_media_info(output)
        if (not probe.has_video or not probe.audio_stream_count or not 0 < output.stat().st_size <= max_bytes
                or abs(probe.duration_sec-max(p.duration_sec for p in probes)) > .25):
            raise PublicMediaError("PUBLIC_MEDIA_MUX_COVERAGE_MISMATCH")
        if check_continue:
            check_continue()
        digest, size = _file_sha(output), output.stat().st_size
        created = False
        try:
            with output.open('rb') as source, destination.open('xb') as target:
                created = True
                for chunk in iter(lambda:source.read(1024*1024),b''):
                    if check_continue:
                        check_continue()
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            return PublicMediaResponse(plan['source_url'],digest,size,'video/mp4',200,plan['source_url'],
                extraction={'plan_sha256':plan['plan_sha256'],'selection_ids':selections,
                    'representation':'COPY_MUXED_NATIVE_TRACKS','components':retained,
                    'coverage':'SELECTED_VIDEO_AND_AUDIO_TRACKS_COMPLETE_NOT_SEMANTICALLY_REVIEWED',
                    'mux_recipe':'ffmpeg-copy-mux/v1','ffmpeg_sha256':_file_sha(ffmpeg)})
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
