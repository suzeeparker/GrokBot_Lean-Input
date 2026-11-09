"""Optional scrape reports: seo, aeo, and schema.

Plain text extraction stays in extract_url.py. These options always write one
JSON file of fixed fields. A missing element is the string "not found".
Extra fetches use the same address, size, time, and redirect limits, stay on
the page origin, and stop after five fetches.
"""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urljoin
import uuid

import extract_url
from extract_url import origin_of, validate_url, write_outputs

ORDER = ("page", "seo", "aeo", "schema")
KNOWN = set(ORDER) | {"all"}
MAX_FETCHES = 5
SITEMAP_URL_CAP = 20
ROBOTS_TEXT_CAP = 4000
LLMS_LINE_CAP = 40
JSONLD_EXCERPT = 240
AI_CRAWLERS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "PerplexityBot",
    "Google-Extended",
    "CCBot",
    "Bingbot",
)
SCHEMA_FIELDS = {
    "Organization": ("name", "url", "logo", "sameAs"),
    "WebSite": ("name", "url"),
    "Article": ("headline", "author", "datePublished", "dateModified"),
    "BlogPosting": ("headline", "author", "datePublished", "dateModified"),
    "Product": ("name", "description"),
    "FAQPage": ("mainEntity",),
    "HowTo": ("name", "step"),
    "BreadcrumbList": ("itemListElement",),
    "Person": ("name", "url"),
    "LocalBusiness": ("name", "address", "telephone"),
}
NOT_FOUND = "not found"


class OptionParse:
    def __init__(self, options=None, task="", error=None):
        self.options = options or []
        self.task = task
        self.error = error


def parse_options(task):
    """Return selected options and the URL task, or an error. No network.

    Leading standalone words before the URL are options. ``all`` selects
    page, seo, aeo, and schema. Duplicates are ignored. An unknown word in
    that position is an error. With no option words, the default is page.
    ``seoul.example`` is not an option word.
    """
    text = task.strip() if isinstance(task, str) else ""
    if not text:
        return OptionParse(["page"], "")
    tokens = text.split()
    url_at = None
    for index, token in enumerate(tokens):
        lowered = token.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            url_at = index
            break
    if url_at is None:
        if tokens and all(token.isalpha() for token in tokens):
            unknowns = [token for token in tokens if token.casefold() not in KNOWN]
            known = [token for token in tokens if token.casefold() in KNOWN]
            if known and unknowns:
                return OptionParse(error=f"Unknown option '{unknowns[0]}'. Options are page, seo, aeo, schema, or all. Nothing was fetched.")
            if known and not unknowns:
                return OptionParse(error="A public HTTP or HTTPS URL is required. Nothing was fetched.")
        return OptionParse(["page"], text)
    prefix = tokens[:url_at]
    selected = []
    index = 0
    while index < len(prefix):
        token = prefix[index]
        word = token.casefold()
        if token.isalpha() and word in KNOWN:
            names = ORDER if word == "all" else (word,)
            for name in names:
                if name not in selected:
                    selected.append(name)
            index += 1
            continue
        break
    if index < len(prefix):
        token = prefix[index]
        if token.isalpha() and token.casefold() not in {"output", "retain"}:
            return OptionParse(error=f"Unknown option '{token}'. Options are page, seo, aeo, schema, or all. Nothing was fetched.")
    if not selected:
        return OptionParse(["page"], text)
    selected = [name for name in ORDER if name in selected]
    rest = " ".join(prefix[index:] + tokens[url_at:])
    return OptionParse(selected, rest)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.in_title = False
        self.title_parts = []
        self.h1s = []
        self.in_h1 = False
        self.h1_parts = []
        self.heading_tag = None
        self.heading_parts = []
        self.question_headings = 0
        self.metas = []
        self.links = []
        self.json_ld_raw = []
        self.in_json_ld = False
        self.json_parts = []
        self.microdata = False
        self.rdfa = False

    def handle_starttag(self, tag, attrs):
        attr = {key.lower(): value or "" for key, value in attrs}
        if "itemscope" in attr or attr.get("itemtype"):
            self.microdata = True
        if attr.get("typeof") or attr.get("vocab"):
            self.rdfa = True
        if tag == "html" and self.lang is None:
            self.lang = attr.get("lang") or attr.get("xml:lang") or None
        if tag == "title":
            self.in_title = True
            self.title_parts = []
        if tag == "h1":
            self.in_h1 = True
            self.h1_parts = []
        if tag in ("h1", "h2", "h3"):
            self.heading_tag = tag
            self.heading_parts = []
        if tag == "meta":
            self.metas.append(attr)
        if tag == "link":
            self.links.append(attr)
        if tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self.in_json_ld = True
            self.json_parts = []

    def handle_endtag(self, tag):
        if tag == "title" and self.in_title:
            self.in_title = False
        if tag == "h1" and self.in_h1:
            text = " ".join("".join(self.h1_parts).split())
            if text:
                self.h1s.append(text)
            self.in_h1 = False
        if tag == self.heading_tag:
            text = " ".join("".join(self.heading_parts).split())
            if text.endswith("?"):
                self.question_headings += 1
            self.heading_tag = None
        if tag == "script" and self.in_json_ld:
            self.json_ld_raw.append("".join(self.json_parts))
            self.in_json_ld = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_h1:
            self.h1_parts.append(data)
        if self.heading_tag:
            self.heading_parts.append(data)
        if self.in_json_ld:
            self.json_parts.append(data)


def _text(value):
    if isinstance(value, str) and value.strip():
        return " ".join(value.split())
    return NOT_FOUND


def _meta_content(metas, name=None, prop=None):
    for attr in metas:
        if name and attr.get("name", "").lower() == name:
            return _text(attr.get("content"))
        if prop and attr.get("property", "").lower() == prop:
            return _text(attr.get("content"))
    return NOT_FOUND


def _link(links, rel):
    for attr in links:
        if rel in {part.lower() for part in attr.get("rel", "").split()}:
            return _text(attr.get("href"))
    return NOT_FOUND


def parse_page(html):
    parser = PageParser()
    parser.feed(html or "")
    parser.close()
    hreflang = []
    for attr in parser.links:
        rels = {part.lower() for part in attr.get("rel", "").split()}
        if "alternate" in rels and attr.get("hreflang") and attr.get("href"):
            hreflang.append({"lang": attr["hreflang"], "href": attr["href"]})
    title = " ".join("".join(parser.title_parts).split())
    return {
        "title": title or NOT_FOUND,
        "meta_description": _meta_content(parser.metas, name="description"),
        "meta_robots": _meta_content(parser.metas, name="robots"),
        "canonical": _link(parser.links, "canonical"),
        "hreflang": hreflang or NOT_FOUND,
        "lang": _text(parser.lang),
        "open_graph": {
            "title": _meta_content(parser.metas, prop="og:title"),
            "description": _meta_content(parser.metas, prop="og:description"),
            "url": _meta_content(parser.metas, prop="og:url"),
            "type": _meta_content(parser.metas, prop="og:type"),
            "image": _meta_content(parser.metas, prop="og:image"),
        },
        "twitter": {
            "card": _meta_content(parser.metas, name="twitter:card"),
            "title": _meta_content(parser.metas, name="twitter:title"),
            "description": _meta_content(parser.metas, name="twitter:description"),
            "image": _meta_content(parser.metas, name="twitter:image"),
        },
        "h1": parser.h1s or NOT_FOUND,
        "json_ld_raw": parser.json_ld_raw,
        "microdata": "present" if parser.microdata else NOT_FOUND,
        "rdfa": "present" if parser.rdfa else NOT_FOUND,
        "question_headings": parser.question_headings,
        "author_meta": _meta_content(parser.metas, name="author"),
        "published_meta": _meta_content(parser.metas, prop="article:published_time"),
        "modified_meta": _meta_content(parser.metas, prop="article:modified_time"),
    }


def parse_robots(text):
    groups = []
    current = None
    sitemaps = []
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "sitemap" and value:
            sitemaps.append(value)
            continue
        if key == "user-agent":
            if current is None or current["rules"]:
                current = {"agents": [value.lower()], "rules": []}
                groups.append(current)
            else:
                current["agents"].append(value.lower())
            continue
        if key in ("allow", "disallow") and current is not None:
            current["rules"].append((key, value))
    return groups, sitemaps


def crawler_directive(text, name):
    """Return allowed, blocked, or not mentioned for one crawler name."""
    groups, _sitemaps = parse_robots(text)
    matched = [group for group in groups if name.lower() in group["agents"]]
    if not matched:
        return "not mentioned"
    rules = matched[0]["rules"]
    disallow_all = any(key == "disallow" and value in ("/", "/*") for key, value in rules)
    allow_all = any(key == "allow" and value in ("/", "") for key, value in rules)
    if disallow_all and not allow_all:
        return "blocked"
    return "allowed"


def parse_json_ld(raw_blocks):
    parsed = []
    invalid = []
    if not raw_blocks:
        return parsed, invalid
    for raw in raw_blocks:
        excerpt = " ".join(raw.split())[:JSONLD_EXCERPT]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            invalid.append({"error": str(exc), "excerpt": excerpt or NOT_FOUND})
            continue
        parsed.append(data)
    return parsed, invalid


def iter_nodes(data):
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item)
        return
    if not isinstance(data, dict):
        return
    graph = data.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            yield from iter_nodes(item)
        return
    yield data


def node_types(node):
    value = node.get("@type")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def type_name(value):
    return value.rstrip("/").split("/")[-1]


def _field_text(value):
    if value is None or value == "" or value == [] or value == {}:
        return NOT_FOUND
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        if isinstance(value.get("name"), str) and value.get("name").strip():
            return _text(value["name"])
        return NOT_FOUND
    if isinstance(value, list):
        names = []
        for item in value:
            rendered = _field_text(item)
            if rendered != NOT_FOUND:
                names.append(rendered)
        return names or NOT_FOUND
    return _text(str(value))


def schema_report(raw_blocks, microdata, rdfa):
    parsed, invalid = parse_json_ld(raw_blocks)
    nodes = []
    for block in parsed:
        nodes.extend(iter_nodes(block))
    found = []
    for node in nodes:
        for name in node_types(node):
            short = type_name(name)
            if short not in found:
                found.append(short)
    types = {}
    for type_key, fields in SCHEMA_FIELDS.items():
        match = next((node for node in nodes if type_key in {type_name(item) for item in node_types(node)}), None)
        if match is None:
            types[type_key] = NOT_FOUND
            continue
        types[type_key] = {field: _field_text(match.get(field)) for field in fields}
    return {
        "json_ld_valid_count": len(parsed),
        "json_ld_invalid": invalid or NOT_FOUND,
        "microdata": microdata,
        "rdfa": rdfa,
        "types_found": found or NOT_FOUND,
        "types": types,
    }


def cap_text(text, limit):
    if not text:
        return NOT_FOUND
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]"


def cap_lines(text, count):
    if not text:
        return NOT_FOUND
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return NOT_FOUND
    chosen = lines[:count]
    body = "\n".join(chosen)
    if len(lines) > count:
        body += "\n[truncated]"
    return body


class FetchBudget:
    def __init__(self, limit=MAX_FETCHES):
        self.limit = limit
        self.used = 0

    def take(self):
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


def _absent_robots():
    return {"url": NOT_FOUND, "http_status": NOT_FOUND, "raw_text": NOT_FOUND, "sitemap_lines": NOT_FOUND}


def _absent_sitemap():
    return {"url": NOT_FOUND, "http_status": NOT_FOUND, "url_count": NOT_FOUND, "first_urls": NOT_FOUND}


def _absent_llms():
    return {"url": NOT_FOUND, "http_status": NOT_FOUND, "first_lines": NOT_FOUND}


def fetch_same_origin(url, origin, budget, allow_tunnel, fetcher):
    if not budget.take():
        return {"ok": False, "http_status": NOT_FOUND, "text": "", "final_url": url, "error": "Fetch limit reached", "warnings": []}
    try:
        if origin_of(url) != tuple(origin):
            return {"ok": False, "http_status": NOT_FOUND, "text": "", "final_url": url, "error": "URL is not on the page origin", "warnings": []}
    except ValueError as exc:
        return {"ok": False, "http_status": NOT_FOUND, "text": "", "final_url": url, "error": str(exc), "warnings": []}
    try:
        return fetcher(url, allow_tunnel=allow_tunnel, require_html=False, lock_origin=origin)
    except (ValueError, TimeoutError) as exc:
        return {"ok": False, "http_status": NOT_FOUND, "text": "", "final_url": url, "error": str(exc), "warnings": []}


def build_seo(page, robots, sitemap, llms, requested, final, warnings):
    return {
        "requested_url": requested,
        "final_url": final,
        "option": "seo",
        "status": "success",
        "error": None,
        "page_meta": {key: page[key] for key in (
            "title", "meta_description", "meta_robots", "canonical", "hreflang", "lang", "open_graph", "twitter", "h1",
        )},
        "robots_txt": robots,
        "sitemap": sitemap,
        "llms_txt": llms,
        "warnings": warnings,
    }


def build_schema(report, requested, final, warnings):
    payload = {
        "requested_url": requested,
        "final_url": final,
        "option": "schema",
        "status": "success",
        "error": None,
        "warnings": warnings,
    }
    payload.update(report)
    return payload


def check_item(check_id, result, detail, suggestion):
    return {"id": check_id, "result": result, "detail": detail, "suggestion": suggestion}


def build_aeo(page, robots_text, llms_ok, schema, requested, final, warnings):
    checks = []
    for name in AI_CRAWLERS:
        if robots_text == NOT_FOUND:
            directive = "not mentioned"
        else:
            directive = crawler_directive(robots_text, name)
        if directive == "allowed":
            result, suggestion = "pass", "No change suggested."
        elif directive == "blocked":
            result, suggestion = "fail", f"Remove the Disallow rule for {name} in robots.txt if that crawler should read the site."
        else:
            result, suggestion = "not found", f"Add a User-agent block for {name} only if you want an explicit allow or block."
        checks.append(check_item(f"robots_{name.lower()}", result, directive, suggestion))
    if llms_ok:
        checks.append(check_item("llms_txt", "pass", "present", "No change suggested."))
    else:
        checks.append(check_item("llms_txt", "not found", NOT_FOUND, "Publish a same-origin /llms.txt if you want a crawler guide."))
    types_found = schema["types_found"] if schema["types_found"] != NOT_FOUND else []
    for type_name_ in ("FAQPage", "HowTo", "Article", "Organization", "BreadcrumbList"):
        if type_name_ in types_found:
            checks.append(check_item(f"schema_{type_name_.lower()}", "pass", "present", "No change suggested."))
        else:
            checks.append(check_item(
                f"schema_{type_name_.lower()}", "not found", NOT_FOUND,
                f"Add JSON-LD @type {type_name_} if this page should declare it.",
            ))
    author_found = page["author_meta"] != NOT_FOUND or _schema_field_present(schema, ("Article", "BlogPosting", "Person"), "author") or _schema_field_present(schema, ("Person",), "name")
    checks.append(check_item(
        "author", "pass" if author_found else "not found",
        page["author_meta"] if page["author_meta"] != NOT_FOUND else NOT_FOUND,
        "No change suggested." if author_found else "Add a visible author in meta or JSON-LD.",
    ))
    dates_found = page["published_meta"] != NOT_FOUND or page["modified_meta"] != NOT_FOUND or _schema_field_present(schema, ("Article", "BlogPosting"), "datePublished")
    checks.append(check_item(
        "dates", "pass" if dates_found else "not found",
        page["published_meta"] if page["published_meta"] != NOT_FOUND else NOT_FOUND,
        "No change suggested." if dates_found else "Add datePublished or article:published_time.",
    ))
    questions = page["question_headings"]
    checks.append(check_item(
        "question_headings", "pass" if questions else "not found",
        str(questions),
        "No change suggested." if questions else "Add a heading that ends with a question mark if the page answers questions.",
    ))
    checks.append(check_item(
        "meta_description", "pass" if page["meta_description"] != NOT_FOUND else "not found",
        page["meta_description"] if page["meta_description"] != NOT_FOUND else NOT_FOUND,
        "No change suggested." if page["meta_description"] != NOT_FOUND else "Add a meta description.",
    ))
    checks.append(check_item(
        "canonical", "pass" if page["canonical"] != NOT_FOUND else "not found",
        page["canonical"] if page["canonical"] != NOT_FOUND else NOT_FOUND,
        "No change suggested." if page["canonical"] != NOT_FOUND else "Add a rel=canonical link.",
    ))
    return {
        "requested_url": requested,
        "final_url": final,
        "option": "aeo",
        "status": "success",
        "error": None,
        "note": "Heuristic checklist only. It does not judge answer quality or call a model.",
        "checks": checks,
        "warnings": warnings,
    }


def _schema_field_present(schema, type_names, field):
    for type_name_ in type_names:
        block = schema["types"].get(type_name_)
        if isinstance(block, dict) and block.get(field) not in (None, NOT_FOUND):
            return True
    return False


def _summary_head(payload, title):
    lines = [f"{title} for {payload['final_url']}", f"Output: {payload.get('output', NOT_FOUND)}"]
    if payload.get("error"):
        lines.append(f"Error: {payload['error']}")
    return lines


def summarize_seo(payload):
    meta = payload["page_meta"]
    robots = payload["robots_txt"]
    sitemap = payload["sitemap"]
    llms = payload["llms_txt"]
    h1 = meta["h1"]
    h1_line = str(len(h1)) if isinstance(h1, list) else NOT_FOUND
    lines = _summary_head(payload, "SEO summary")
    lines.extend([
        f"Title: {meta['title']}",
        f"Meta description: {meta['meta_description']}",
        f"Canonical: {meta['canonical']}",
        f"H1 count: {h1_line}",
        f"Robots.txt: {robots['http_status']}",
        f"Sitemap URLs: {sitemap['url_count']}",
        f"llms.txt: {llms['http_status']}",
    ])
    return "\n".join(lines)


def summarize_schema(payload):
    found = payload["types_found"]
    found_line = ", ".join(found) if isinstance(found, list) else NOT_FOUND
    missing = [name for name, value in payload["types"].items() if value == NOT_FOUND]
    invalid = payload["json_ld_invalid"]
    invalid_count = len(invalid) if isinstance(invalid, list) else 0
    lines = _summary_head(payload, "Schema summary")
    lines.extend([
        f"JSON-LD valid blocks: {payload['json_ld_valid_count']}",
        f"JSON-LD invalid blocks: {invalid_count}",
        f"Types found: {found_line}",
        f"Types not found: {', '.join(missing) if missing else 'none'}",
        f"Microdata: {payload['microdata']}",
        f"RDFa: {payload['rdfa']}",
    ])
    return "\n".join(lines)


def summarize_aeo(payload):
    counts = {"pass": 0, "fail": 0, "not found": 0}
    lines = _summary_head(payload, "AEO summary")
    for check in payload["checks"]:
        counts[check["result"]] = counts.get(check["result"], 0) + 1
        lines.append(f"- {check['id']}: {check['result']} — {check['suggestion']}")
    lines.insert(2, f"pass {counts['pass']}, fail {counts['fail']}, not found {counts['not found']}")
    lines.append(payload["note"])
    return "\n".join(lines)


def _robots_record(fetched, url):
    if not fetched or not fetched.get("ok"):
        status = fetched.get("http_status", NOT_FOUND) if fetched else NOT_FOUND
        return {"url": url, "http_status": status if status else NOT_FOUND, "raw_text": NOT_FOUND, "sitemap_lines": NOT_FOUND}, NOT_FOUND, []
    text = fetched.get("text") or ""
    _groups, sitemaps = parse_robots(text)
    return {
        "url": fetched.get("final_url") or url,
        "http_status": fetched.get("http_status"),
        "raw_text": cap_text(text, ROBOTS_TEXT_CAP),
        "sitemap_lines": sitemaps or NOT_FOUND,
    }, text, sitemaps


def _sitemap_record(fetched, url):
    if not fetched or not fetched.get("ok"):
        status = fetched.get("http_status", NOT_FOUND) if fetched else NOT_FOUND
        return {"url": url or NOT_FOUND, "http_status": status if status else NOT_FOUND, "url_count": NOT_FOUND, "first_urls": NOT_FOUND}
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", fetched.get("text") or "", flags=re.I)
    return {
        "url": fetched.get("final_url") or url,
        "http_status": fetched.get("http_status"),
        "url_count": len(locs),
        "first_urls": locs[:SITEMAP_URL_CAP] or NOT_FOUND,
    }


def _llms_record(fetched, url):
    if not fetched or not fetched.get("ok"):
        status = fetched.get("http_status", NOT_FOUND) if fetched else NOT_FOUND
        return {"url": url, "http_status": status if status else NOT_FOUND, "first_lines": NOT_FOUND}, False
    return {
        "url": fetched.get("final_url") or url,
        "http_status": fetched.get("http_status"),
        "first_lines": cap_lines(fetched.get("text") or "", LLMS_LINE_CAP),
    }, True


def page_payload(requested, final, html, warnings):
    result = {
        "requested_url": requested,
        "final_url": final,
        "title": None,
        "author": None,
        "publication_date": None,
        "text": None,
        "status": "error",
        "warnings": list(warnings),
        "error": None,
    }
    try:
        extracted = extract_url.extract_html(html, final)
    except ValueError as exc:
        result["error"] = str(exc)
        return result
    result["title"] = extracted["title"]
    result["author"] = extracted["author"]
    result["publication_date"] = extracted["publication_date"]
    result["text"] = extracted["text"]
    result["warnings"].extend(extracted["warnings"])
    result["status"] = "success"
    return result


def gather(url, options, allow_tunnel=False, fetcher=None):
    """Fetch the page once, then robots, sitemap, and llms.txt at most once."""
    fetch = fetcher or extract_url.fetch_resource
    budget = FetchBudget()
    warnings = []
    if not budget.take():
        raise ValueError("Fetch limit reached")
    page_fetch = fetch(url, allow_tunnel=allow_tunnel, require_html=True, lock_origin=None)
    if not page_fetch.get("ok"):
        raise ValueError(page_fetch.get("error") or "Page fetch failed")
    final = page_fetch["final_url"]
    origin = origin_of(final)
    html = page_fetch["text"]
    warnings.extend(page_fetch.get("warnings") or [])
    parsed = parse_page(html)
    robots = _absent_robots()
    robots_text = NOT_FOUND
    sitemap = _absent_sitemap()
    llms = _absent_llms()
    llms_ok = False
    if "seo" in options or "aeo" in options:
        robots_url = urljoin(final, "/robots.txt")
        fetched = fetch_same_origin(robots_url, origin, budget, allow_tunnel, fetch)
        warnings.extend(fetched.get("warnings") or [])
        robots, robots_text, sitemaps = _robots_record(fetched, robots_url)
        if "seo" in options:
            sitemap_url = next((item for item in sitemaps if _safe_origin(item, origin)), None)
            if sitemap_url is None:
                sitemap_url = urljoin(final, "/sitemap.xml")
            fetched_map = fetch_same_origin(sitemap_url, origin, budget, allow_tunnel, fetch)
            warnings.extend(fetched_map.get("warnings") or [])
            sitemap = _sitemap_record(fetched_map, sitemap_url)
        llms_url = urljoin(final, "/llms.txt")
        fetched_llms = fetch_same_origin(llms_url, origin, budget, allow_tunnel, fetch)
        warnings.extend(fetched_llms.get("warnings") or [])
        llms, llms_ok = _llms_record(fetched_llms, llms_url)
    report = None
    if "schema" in options or "aeo" in options:
        report = schema_report(parsed["json_ld_raw"], parsed["microdata"], parsed["rdfa"])
    payloads = {}
    if "page" in options:
        payloads["page"] = page_payload(url, final, html, warnings)
    if "seo" in options:
        payloads["seo"] = build_seo(parsed, robots, sitemap, llms, url, final, warnings)
    if "aeo" in options:
        payloads["aeo"] = build_aeo(parsed, robots_text, llms_ok, report, url, final, warnings)
    if "schema" in options:
        payloads["schema"] = build_schema(report, url, final, warnings)
    return payloads, html


def _safe_origin(url, origin):
    try:
        return origin_of(url) == tuple(origin)
    except ValueError:
        return False


def error_payload(option, url, message):
    if option == "page":
        return {
            "requested_url": url if isinstance(url, str) else None,
            "final_url": None,
            "title": None,
            "author": None,
            "publication_date": None,
            "text": None,
            "status": "error",
            "warnings": [],
            "error": message,
        }
    base = {
        "requested_url": url if isinstance(url, str) else None,
        "final_url": NOT_FOUND,
        "option": option,
        "status": "error",
        "error": message,
        "warnings": [],
    }
    if option == "seo":
        base.update({
            "page_meta": {key: NOT_FOUND for key in (
                "title", "meta_description", "meta_robots", "canonical", "hreflang", "lang", "open_graph", "twitter", "h1",
            )},
            "robots_txt": _absent_robots(),
            "sitemap": _absent_sitemap(),
            "llms_txt": _absent_llms(),
        })
        base["page_meta"]["open_graph"] = {key: NOT_FOUND for key in ("title", "description", "url", "type", "image")}
        base["page_meta"]["twitter"] = {key: NOT_FOUND for key in ("card", "title", "description", "image")}
    elif option == "schema":
        base.update(schema_report([], NOT_FOUND, NOT_FOUND))
    else:
        base["note"] = "Heuristic checklist only. It does not judge answer quality or call a model."
        base["checks"] = []
    return base


def default_stem():
    return Path.home() / "Tools" / "lean-input" / "output" / f"page-{uuid.uuid4().hex}.json"


def files_for(stem, options):
    stem = Path(stem)
    if stem.suffix == ".json":
        stem = stem.with_suffix("")
    paths = {}
    for name in ORDER:
        if name not in options:
            continue
        paths[name] = stem.with_name(stem.name + ".json") if name == "page" else stem.with_name(f"{stem.name}.{name}.json")
    return paths


def summarize_page(payload):
    lines = _summary_head(payload, "Page summary")
    lines.append(f"Title: {payload.get('title') or NOT_FOUND}")
    lines.append(f"Status: {payload.get('status')}")
    return "\n".join(lines)


def summarize_selected(payloads):
    parts = []
    for name in ORDER:
        if name not in payloads:
            continue
        if name == "page":
            parts.append(summarize_page(payloads[name]))
        elif name == "seo":
            parts.append(summarize_seo(payloads[name]))
        elif name == "aeo":
            parts.append(summarize_aeo(payloads[name]))
        else:
            parts.append(summarize_schema(payloads[name]))
    return "\n\n".join(parts)


def run_selected(options, url, stem, allow_tunnel=False, fetcher=None):
    paths = files_for(stem, options)
    code = 0
    try:
        validate_url(url)
    except ValueError as exc:
        payloads = {name: error_payload(name, url, str(exc)) for name in options}
        code = 2
        html = None
    else:
        try:
            payloads, html = gather(url, options, allow_tunnel=allow_tunnel, fetcher=fetcher)
        except TimeoutError as exc:
            payloads = {name: error_payload(name, url, str(exc)) for name in options}
            code = 1
            html = None
        except ValueError as exc:
            payloads = {name: error_payload(name, url, str(exc)) for name in options}
            code = 1
            html = None
    for name in options:
        payloads[name]["output"] = str(paths[name])
    summary = summarize_selected(payloads)
    written = {}
    for name in ORDER:
        if name not in payloads:
            continue
        stored = {key: value for key, value in payloads[name].items() if key != "output"}
        metrics = write_outputs(stored, paths[name], html if name == "page" else None, retain=False)
        written[name] = {"output": str(paths[name]), "metrics": metrics}
        if name == "page" and stored.get("status") != "success" and code == 0:
            code = 1
    return code, summary, written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write page, seo, aeo, and schema JSON reports.")
    parser.add_argument("items", nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--target", choices=("bot", "mac"))
    args = parser.parse_args(argv)
    if len(args.items) < 2:
        print("A public HTTP or HTTPS URL is required. Nothing was fetched.", file=sys.stderr)
        return 2
    url = args.items[-1]
    raw_options = args.items[:-1]
    parsed = parse_options(" ".join(raw_options + [url]))
    if parsed.error:
        print(parsed.error, file=sys.stderr)
        return 2
    stem = Path(args.output).expanduser() if args.output else default_stem()
    try:
        code, summary, written = run_selected(
            parsed.options, url, stem, allow_tunnel=args.target == "bot",
        )
    except OSError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    print(summary)
    print(json.dumps({"status": "error" if code else "success", "outputs": written}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
