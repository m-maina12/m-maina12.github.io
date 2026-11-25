#!/usr/bin/env python3
"""Create Jekyll publication documents for new public works in the configured ORCID."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS_DIR = ROOT / "_publications"
ORCID_NS = {
    "activities": "http://www.orcid.org/ns/activities",
    "common": "http://www.orcid.org/ns/common",
    "work": "http://www.orcid.org/ns/work",
}


def fetch(url: str, accept: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "m-maina12.github.io ORCID publication sync",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def optional_json(url: str) -> dict | None:
    try:
        return json.loads(fetch(url, "application/json"))
    except urllib.error.HTTPError as error:
        if error.code in (404, 429, 503):
            print(f"Metadata source returned HTTP {error.code}: {url}", file=sys.stderr)
            return None
        raise


def configured_orcid() -> str:
    config = (ROOT / "_config.yml").read_text(encoding="utf-8")
    match = re.search(
        r"^\s*orcid\s*:\s*[\"']?https?://orcid\.org/([\dX-]+)",
        config,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        raise RuntimeError("Could not find a configured ORCID URL in _config.yml")
    return match.group(1)


def node_text(node: ET.Element | None, path: str) -> str:
    if node is None:
        return ""
    value = node.findtext(path, namespaces=ORCID_NS)
    return value.strip() if value else ""


def canonical_doi(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value.rstrip(".,;:)]}").lower()


def doi_from(node: ET.Element | None) -> str:
    if node is None:
        return ""
    for external_id in node.findall(".//common:external-id", ORCID_NS):
        if node_text(external_id, "common:external-id-type").lower() == "doi":
            value = node_text(external_id, "common:external-id-normalized")
            return canonical_doi(value or node_text(external_id, "common:external-id-value"))
    return ""


def existing_records() -> tuple[set[str], set[str], set[str]]:
    dois: set[str] = set()
    titles: set[str] = set()
    put_codes: set[str] = set()
    for path in PUBLICATIONS_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"10\.\d{4,9}/[^\s\"'<>]+", content, re.IGNORECASE):
            dois.add(canonical_doi(match.group(0)))
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        if title_match:
            titles.add(normalize_title(title_match.group(1)))
        put_match = re.search(r"^orcid_put_code:\s*[\"']?(\d+)", content, re.MULTILINE)
        if put_match:
            put_codes.add(put_match.group(1))
    return dois, titles, put_codes


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


def publication_date(node: ET.Element | None) -> date | None:
    if node is None:
        return None
    date_node = node.find("common:publication-date", ORCID_NS)
    if date_node is None:
        return None
    year = node_text(date_node, "common:year")
    if not year:
        return None
    month = node_text(date_node, "common:month") or "1"
    day = node_text(date_node, "common:day") or "1"
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def crossref_date(message: dict) -> date | None:
    for field in ("published-online", "published-print", "published", "issued"):
        parts = message.get(field, {}).get("date-parts", [[]])[0]
        if parts:
            try:
                return date(
                    int(parts[0]),
                    int(parts[1]) if len(parts) > 1 else 1,
                    int(parts[2]) if len(parts) > 2 else 1,
                )
            except ValueError:
                continue
    return None


def clean_crossref_abstract(value: str) -> str:
    value = re.sub(
        r"<jats:title[^>]*>\s*abstract\s*</jats:title>",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"<jats:title[^>]*>(.*?)</jats:title>",
        lambda match: f"\n**{match.group(1).strip()}:** ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    value = re.sub(r"</jats:sec\s*>", "\n\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    paragraphs = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def openalex_abstract(doi: str) -> str:
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    data = optional_json(url)
    inverted = data.get("abstract_inverted_index") if data else None
    if not inverted:
        return ""
    words = [""] * (max(index for indexes in inverted.values() for index in indexes) + 1)
    for word, indexes in inverted.items():
        for index in indexes:
            words[index] = word
    return " ".join(words)


def crossref_metadata(doi: str) -> dict:
    data = optional_json(f"https://api.crossref.org/works/{doi}")
    return data.get("message", {}) if data else {}


def get_record(summary: ET.Element, orcid: str) -> dict:
    put_code = summary.attrib["put-code"]
    detail_url = f"https://pub.orcid.org/v3.0/{orcid}/work/{put_code}"
    detail = ET.fromstring(fetch(detail_url, "application/vnd.orcid+xml"))
    doi = doi_from(detail) or doi_from(summary)
    crossref = crossref_metadata(doi) if doi else {}

    title = (
        node_text(detail, "work:title/common:title")
        or node_text(summary, "work:title/common:title")
        or (crossref.get("title") or [""])[0]
    )
    if not title:
        raise RuntimeError(f"ORCID work {put_code} has no title")

    authors = []
    for contributor in detail.findall("work:contributors/work:contributor", ORCID_NS):
        role = node_text(contributor, "work:contributor-attributes/work:contributor-role")
        author = node_text(contributor, "work:credit-name")
        if author and (not role or role.casefold() == "author"):
            authors.append(author)
    if not authors:
        authors = [
            " ".join(filter(None, (author.get("given"), author.get("family"))))
            for author in crossref.get("author", [])
        ]

    venue = (
        node_text(detail, "work:journal-title")
        or node_text(summary, "work:journal-title")
        or (crossref.get("container-title") or [""])[0]
    )
    published = publication_date(detail) or publication_date(summary) or crossref_date(crossref)
    if published is None:
        year = crossref.get("published", {}).get("date-parts", [[None]])[0][0]
        if year:
            published = date(int(year), 1, 1)
        else:
            raise RuntimeError(f"ORCID work {put_code} has no publication date")

    abstract = clean_crossref_abstract(crossref.get("abstract", ""))
    if not abstract:
        abstract = node_text(detail, "work:short-description")
    if not abstract and doi:
        abstract = openalex_abstract(doi)
    if doi and not abstract:
        print(f"No abstract found for DOI {doi}", file=sys.stderr)

    doi_url = f"https://doi.org/{doi}" if doi else ""
    paper_url = doi_url or node_text(detail, "common:url") or node_text(summary, "common:url")
    if not paper_url:
        raise RuntimeError(f"ORCID work {put_code} has no DOI or paper URL")

    work_type = node_text(detail, "work:type").casefold()
    arxiv_match = re.search(r"10\.48550/arxiv\.(.+)$", doi, re.IGNORECASE)
    is_preprint = "preprint" in work_type or arxiv_match is not None or "arxiv" in venue.casefold()
    if is_preprint:
        category = "preprints"
    elif "conference" in work_type:
        category = "conferences"
    elif "book" in work_type:
        category = "books"
    else:
        category = "manuscripts"
    crossref_pdf = next(
        (
            link.get("URL", "")
            for link in crossref.get("link", [])
            if link.get("content-type", "").casefold() == "application/pdf"
        ),
        "",
    )
    paper_download_url = (
        f"https://arxiv.org/pdf/{arxiv_match.group(1)}"
        if arxiv_match
        else crossref_pdf or paper_url
    )

    return {
        "abstract": abstract,
        "authors": authors,
        "category": category,
        "date": published.isoformat(),
        "doi": doi,
        "paper_download_url": paper_download_url,
        "paper_url": paper_url,
        "put_code": put_code,
        "title": title,
        "venue": venue or ("Preprint" if is_preprint else ""),
    }


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def document(record: dict) -> tuple[str, str]:
    identity = record["doi"] or record["put_code"]
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]
    slug = unicodedata.normalize("NFKD", record["title"])
    slug = slug.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:65].rstrip("-")
    permalink = f"{record['date']}-{slug}-{digest}"

    lines = [
        "---",
        f"title: {yaml_string(record['title'])}",
        "collection: publications",
        f"category: {record['category']}",
        f"permalink: {yaml_string('/publication/' + permalink)}",
        f"date: {record['date']}",
        f"venue: {yaml_string(record['venue'])}",
        "excerpt: ''",
        f"paperurl: {yaml_string(record['paper_url'])}",
        f"paperdownloadurl: {yaml_string(record['paper_download_url'])}",
        f"orcid_put_code: {yaml_string(record['put_code'])}",
        "authors:",
    ]
    lines.extend(f"  - {yaml_string(author)}" for author in record["authors"])
    if record["abstract"]:
        lines.append("abstract: |")
        lines.extend(f"  {line}" if line else "" for line in record["abstract"].splitlines())
    lines.extend(["---", ""])
    return f"{record['date']}-{slug}-{digest}.md", "\n".join(lines)


def main() -> None:
    orcid = configured_orcid()
    works_url = f"https://pub.orcid.org/v3.0/{orcid}/works"
    root = ET.fromstring(fetch(works_url, "application/vnd.orcid+xml"))
    existing_dois, existing_titles, existing_put_codes = existing_records()

    summaries = []
    for group in root.findall("activities:group", ORCID_NS):
        summaries.extend(group.findall("work:work-summary", ORCID_NS))

    added = 0
    seen: set[str] = set()
    for summary in summaries:
        doi = doi_from(summary)
        put_code = summary.attrib.get("put-code", "")
        identity = doi or put_code
        if (
            not identity
            or identity in seen
            or doi in existing_dois
            or put_code in existing_put_codes
            or normalize_title(node_text(summary, "work:title/common:title")) in existing_titles
        ):
            continue
        seen.add(identity)
        record = get_record(summary, orcid)
        filename, content = document(record)
        destination = PUBLICATIONS_DIR / filename
        if destination.exists():
            continue
        destination.write_text(content, encoding="utf-8")
        print(f"Added {record['title']} ({record['date']})")
        added += 1

    if added == 0:
        print("No new public ORCID works found.")
    else:
        print(f"Added {added} publication(s) from ORCID {orcid}.")


if __name__ == "__main__":
    main()
