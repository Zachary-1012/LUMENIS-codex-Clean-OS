#!/usr/bin/env python3
"""Reviewable local HTTP replay. Default: offline dry-run, no approval or writes.

Phases: dry-run -> registration-prepare -> registration-apply (exact resource)
-> profiles-prepare -> profiles-apply (exact saved-plan SHA256).
Only existing server owners authorize, register and import. No keys, DB access,
auto-adoption, fuzzy identity matching, or external network destinations.
"""

from __future__ import annotations
import argparse, copy, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_lines(path):
    return [
        json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
    ]


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(target)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirects are disabled; use the exact local runtime URL")


class APIError(RuntimeError):
    def __init__(self, status, result):
        self.status, self.result = status, result
        super().__init__(
            json.dumps({"status": status, "response": result}, ensure_ascii=False)
        )


class Client:
    def __init__(self, base_url):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("This replay tool requires a local loopback HTTP runtime")
        self.base_url = base_url.rstrip("/")
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, method, path, body=None, scope=None):
        headers = {"Content-Type": "application/json"}
        if scope:
            headers.update(
                {
                    "X-Domain-ID": "BMP" if scope["domain_id"] == "zbmp" else "CTH",
                    "X-Lumenis-Context-Mode": "FOCUS",
                }
            )
            headers[
                "X-Brand-Focus-ID" if scope["brand_focus_id"] else "X-Subject-ID"
            ] = (scope["brand_focus_id"] or scope["subject_id"])
        request = Request(
            self.base_url + path,
            data=canonical(body) if body is not None else None,
            method=method,
            headers=headers,
        )
        try:
            response = self.opener.open(request, timeout=120)
        except HTTPError as error:
            response = error
        result = json.loads(response.read())
        if response.status >= 400 or not result.get("ok"):
            raise APIError(response.status, result)
        return result


def package(baseline, bundle_paths):
    identities = {}
    for row in read_lines(baseline):
        bid = row.get("seed_key") or f"{row['_baseline_file']}:{row['_baseline_line']}"
        identity = {
            key: row.get(key, "" if key != "keywords" else [])
            for key in (
                "domain_id",
                "subject_type",
                "name_en",
                "name_zh",
                "industry",
                "keywords",
            )
        }
        if bid in identities:
            raise ValueError("Duplicate baseline identity: " + bid)
        identities[bid] = identity
    bundles = []
    seen = set()
    for path in bundle_paths:
        for bundle in read_lines(path):
            bid = bundle["baseline_id"]
            identity = identities.get(bid)
            if (
                bid in seen
                or identity is None
                or (identity["name_en"], identity["name_zh"], identity["domain_id"])
                != (
                    bundle["baseline_name_en"],
                    bundle["baseline_name_zh"],
                    bundle["domain_id"],
                )
            ):
                raise ValueError("Ambiguous or mismatched baseline candidate: " + bid)
            if (
                bundle["manifest_template"]["entity"] is not None
                or bundle["manifest_template"]["review"]
            ):
                raise ValueError("Candidate package must remain unbound and unadopted")
            seen.add(bid)
            bundles.append(bundle)
    return {
        "entries": [
            {"baseline_id": key, "identity": value} for key, value in identities.items()
        ],
        "bundles": bundles,
        "input_sha256": {
            str(path): hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for path in [baseline, *bundle_paths]
        },
    }


def prepare_profiles(client, inputs, mapping):
    if mapping.get("entries_sha256") != digest(inputs["entries"]):
        raise ValueError("Registration receipt is for a different identity package")
    entries = {row["baseline_id"]: row["identity"] for row in inputs["entries"]}
    resolved = {
        row["baseline_id"]: row["subject"]
        for row in mapping["results"]
        if row["status"] in {"CREATED", "EXISTING"}
    }
    groups, skipped = {}, []
    for bundle in inputs["bundles"]:
        bid = bundle["baseline_id"]
        subject = resolved.get(bid)
        if subject is None:
            skipped.append({"baseline_id": bid, "reason": "IDENTITY_NOT_RESOLVED"})
            continue
        expected = entries[bid]
        if any(
            subject[key] != expected[key]
            for key in ("domain_id", "subject_type", "name_en", "name_zh")
        ):
            raise ValueError("Registration receipt identity mismatch: " + bid)
        scope = {
            "domain_id": "zbmp" if subject["domain_id"] == "BMP" else "cth",
            "subject_id": (
                subject["subject_id"] if subject["domain_id"] == "CTH" else None
            ),
            "brand_focus_id": (
                subject["brand_focus_id"] if subject["domain_id"] == "BMP" else None
            ),
            "global_scope": False,
        }
        key = digest(scope)
        group = groups.setdefault(
            key,
            {
                "scope": scope,
                "baseline_ids": [],
                "sources": {},
                "assertions": {},
                "temporal_limitations": [],
            },
        )
        group["baseline_ids"].append(bid)
        group["temporal_limitations"].extend(bundle.get("temporal_limitations", []))
        for kind in ("sources", "assertions"):
            for row in bundle["manifest_template"][kind]:
                previous = group[kind].get(row["id"])
                if previous is not None and previous != row:
                    raise ValueError("Conflicting statement ID: " + row["id"])
                group[kind][row["id"]] = row
    prepared = []
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for group in groups.values():
        scope = group["scope"]
        current = client.call("GET", "/api/experience/entity-profiles", scope=scope)[
            "result"
        ]["current"]
        manifest = {
            "schema": "lumenis.entity-profile-assertions/v1",
            "entity": scope,
            "version": current["manifest"]["version"] + 1 if current else 1,
            "parent_sha256": current["sha256"] if current else None,
            "imported_at": stamp,
            "request_id": "foundation-"
            + digest(
                {
                    "inputs": inputs["input_sha256"],
                    "scope": scope,
                    "parent": current["sha256"] if current else None,
                }
            ),
            "sources": list(group["sources"].values()),
            "assertions": list(group["assertions"].values()),
            "review": {},
        }
        # Updates retain earlier statements and explicit reviews unless this plan
        # encounters an ID/content conflict, which requires separate resolution.
        if current:
            for kind in ("sources", "assertions"):
                combined = {row["id"]: row for row in current["manifest"][kind]}
                for row in manifest[kind]:
                    if row["id"] in combined and combined[row["id"]] != row:
                        raise ValueError("Existing statement ID conflict: " + row["id"])
                    combined[row["id"]] = row
                manifest[kind] = list(combined.values())
            manifest["review"] = copy.deepcopy(current["manifest"]["review"])
        preview = client.call(
            "POST", "/api/experience/entity-profiles", {"manifest": manifest}, scope
        )
        prepared.append(
            {
                "baseline_ids": group["baseline_ids"],
                "manifest": manifest,
                "resource": preview["resource"],
                "manifest_sha256": preview["manifest_sha256"],
                "temporal_limitations": group["temporal_limitations"],
            }
        )
    return {
        "schema": "lumenis.profile-replay-plan/v1",
        "input_sha256": inputs["input_sha256"],
        "items": prepared,
        "skipped": skipped,
        "review_requirement": "Review each bound identity, source excerpt, historical date, conflicts and exact resources before confirming this plan hash.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=[
            "dry-run",
            "registration-prepare",
            "registration-apply",
            "profiles-prepare",
            "profiles-apply",
        ],
        default="dry-run",
    )
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--bundles", action="append", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18372")
    parser.add_argument("--output", required=True)
    parser.add_argument("--registration-receipt")
    parser.add_argument("--plan")
    parser.add_argument("--confirmed-resource")
    parser.add_argument("--confirmed-plan-sha256")
    parser.add_argument("--resume-index", type=int, default=0)
    args = parser.parse_args(argv)
    inputs = package(args.baseline, args.bundles)
    if args.mode == "dry-run":
        result = {
            "mode": "DRY_RUN_NO_HTTP_NO_WRITES",
            "identities": len(inputs["entries"]),
            "candidate_bundles": len(inputs["bundles"]),
            "assertions": sum(
                len(x["manifest_template"]["assertions"]) for x in inputs["bundles"]
            ),
            "input_sha256": inputs["input_sha256"],
            "entries": inputs["entries"],
            "registered_ids": None,
            "adopted_fields": None,
        }
    else:
        client = Client(args.base_url)
        if args.mode.startswith("registration-"):
            preview = client.call(
                "POST", "/api/settings/subjects/batch", {"entries": inputs["entries"]}
            )
            if args.mode == "registration-prepare":
                result = preview
            else:
                if args.confirmed_resource != preview["resource"]:
                    raise ValueError(
                        "Review registration-prepare output and provide its exact --confirmed-resource"
                    )
                try:
                    result = client.call(
                        "POST",
                        "/api/settings/subjects/batch",
                        {
                            "entries": inputs["entries"],
                            "mode": "apply",
                            "confirm": True,
                            "confirmed_resource": args.confirmed_resource,
                            "resume_index": args.resume_index,
                        },
                    )
                except APIError as exc:
                    result = exc.result
                    result["entries_sha256"] = digest(inputs["entries"])
                    if args.resume_index and Path(args.output).exists():
                        previous = json.loads(Path(args.output).read_text())
                        if previous.get("entries_sha256") == result["entries_sha256"]:
                            result["results"] = previous["results"] + result.get(
                                "results", []
                            )
                    save(args.output, result)
                    raise
                result["entries_sha256"] = digest(inputs["entries"])
                # Resume keeps earlier verified results; never replaces conflicts.
                if args.resume_index and Path(args.output).exists():
                    old = json.loads(Path(args.output).read_text())
                    if old.get("entries_sha256") != result["entries_sha256"]:
                        raise ValueError("Resume receipt package mismatch")
                    result["results"] = old["results"] + result["results"]
        elif args.mode == "profiles-prepare":
            if not args.registration_receipt:
                raise ValueError("--registration-receipt is required")
            result = prepare_profiles(
                client, inputs, json.loads(Path(args.registration_receipt).read_text())
            )
        else:
            if not args.plan:
                raise ValueError("--plan is required")
            plan_bytes = Path(args.plan).read_bytes()
            if args.confirmed_plan_sha256 != hashlib.sha256(plan_bytes).hexdigest():
                raise ValueError(
                    "Review the saved plan and provide its exact file --confirmed-plan-sha256"
                )
            plan = json.loads(plan_bytes)
            if plan["input_sha256"] != inputs["input_sha256"]:
                raise ValueError("Inputs changed since plan preparation")
            result = {
                "plan_sha256": args.confirmed_plan_sha256,
                "results": [],
                "skipped": plan["skipped"],
                "state": "IN_PROGRESS",
            }
            for index, item in enumerate(plan["items"]):
                try:
                    reply = client.call(
                        "POST",
                        "/api/experience/entity-profiles",
                        {
                            "mode": "import",
                            "manifest": item["manifest"],
                            "confirmed_resource": item["resource"],
                            "confirm": True,
                        },
                        item["manifest"]["entity"],
                    )
                    result["results"].append(
                        {
                            "index": index,
                            "baseline_ids": item["baseline_ids"],
                            "result": reply["result"],
                        }
                    )
                except Exception as exc:
                    result.update(state="PARTIAL", resume_index=index, error=str(exc))
                    save(args.output, result)
                    raise
                save(args.output, result)
            result["state"] = "COMPLETED"
    save(args.output, result)
    print(
        json.dumps(
            {
                "output": args.output,
                "sha256": hashlib.sha256(Path(args.output).read_bytes()).hexdigest(),
                "mode": args.mode,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
