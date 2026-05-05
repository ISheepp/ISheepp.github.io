from __future__ import annotations

import argparse
import json
import re
import subprocess
import shutil
import urllib.error
import urllib.request
from pathlib import Path

IPFS_URL_RE = re.compile(r"ipfs://([A-Za-z0-9]+)")
TITLE_HEADING_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
HTML_IMAGE_RE = re.compile(
    r'<img\b[^>]*\bsrc="(?P<src>[^"]+)"[^>]*>',
    re.IGNORECASE,
)
IPFS_GATEWAYS = (
    "https://ipfs.crossbell.io/ipfs/{hash}?img-format=auto&img-onerror=redirect&img-quality=75&img-width=1920",
    "https://ipfs.crossbell.io/ipfs/{hash}",
    "https://dweb.link/ipfs/{hash}",
    "https://ipfs.io/ipfs/{hash}",
    "https://cloudflare-ipfs.com/ipfs/{hash}",
    "https://gateway.pinata.cloud/ipfs/{hash}",
)


def crossbell_image_url(ipfs_hash: str) -> str:
    return (
        f"https://ipfs.crossbell.io/ipfs/{ipfs_hash}"
        "?img-format=auto&img-onerror=redirect&img-quality=75&img-width=1920"
    )


def unresolved_image_marker(ipfs_hash: str) -> str:
    return f"./attachments/{ipfs_hash}"


def load_note(note_path: Path) -> dict:
    with note_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def slug_from_note(note: dict) -> str:
    content = note["metadata"]["content"]
    attributes = content.get("attributes", [])
    for attribute in attributes:
        if attribute.get("trait_type") == "xlog_slug":
            slug = str(attribute.get("value", "")).strip()
            if slug:
                return slug
    note_id = note.get("noteId")
    return f"note-{note_id}"


def attachment_source_dir(notes_markdown_root: Path, character_id: int, note_id: int) -> Path | None:
    matches = sorted(notes_markdown_root.glob(f"{character_id}-{note_id} -*"))
    for match in matches:
        candidate = match / "attachments"
        if candidate.is_dir():
            return candidate
    return None


def extract_ipfs_hashes(text: str) -> list[str]:
    return list(dict.fromkeys(IPFS_URL_RE.findall(text)))


def strip_leading_blank_lines(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def normalize_body(title: str, raw: str) -> str:
    text = raw.replace("\r\n", "\n").strip()
    if not text:
        return ""

    lines = text.split("\n")
    lines = strip_leading_blank_lines(lines)

    if lines and lines[0].strip() == f"# {title}":
        lines.pop(0)
        lines = strip_leading_blank_lines(lines)

    if lines and lines[0].strip() == "---":
        closing = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                closing = idx
                break
        if closing is not None:
            lines = lines[closing + 1 :]
            lines = strip_leading_blank_lines(lines)

    if lines and lines[0].strip() == f"# {title}":
        lines.pop(0)
        lines = strip_leading_blank_lines(lines)

    return "\n".join(lines).strip()


def build_front_matter(data: dict) -> str:
    lines = ["---"]
    lines.append(f'title: {yaml_quote(data["title"])}')
    lines.append(f'date: {yaml_quote(data["date"])}')
    if data.get("slug"):
        lines.append(f'slug: {yaml_quote(data["slug"])}')
    if data.get("summary"):
        lines.append(f'summary: {yaml_quote(data["summary"])}')
    tags = [tag for tag in data.get("tags", []) if tag and tag != "post"]
    if tags:
        rendered_tags = ", ".join(yaml_quote(tag) for tag in tags)
        lines.append(f"tags: [{rendered_tags}]")
    lines.append("draft: false")
    lines.append("---")
    return "\n".join(lines)


def rewrite_ipfs_urls(content: str, mapping: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        ipfs_hash = match.group(1)
        return mapping.get(ipfs_hash, match.group(0))

    return IPFS_URL_RE.sub(replace, content)


def normalize_html_images(content: str) -> str:
    def replace(match: re.Match[str]) -> str:
        src = match.group("src")
        return f"![image]({src})"

    return HTML_IMAGE_RE.sub(replace, content)


def detect_image_extension(path: Path | None = None, data: bytes | None = None, content_type: str | None = None) -> str | None:
    header = data
    if header is None and path is not None:
        header = path.read_bytes()[:16]

    if header:
        if header.startswith(b"\xff\xd8\xff"):
            return ".jpeg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return ".gif"
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return ".webp"
        if header.startswith(b"BM"):
            return ".bmp"
        if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
            return ".tiff"
        if header.lstrip().startswith(b"<svg") or b"<svg" in header.lower():
            return ".svg"

    if content_type:
        content_type = content_type.split(";", 1)[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpeg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
        }
        return mapping.get(content_type)

    return None


def download_ipfs(ipfs_hash: str) -> tuple[bytes, str | None]:
    last_error: Exception | None = None
    for gateway in IPFS_GATEWAYS:
        url = gateway.format(hash=ipfs_hash)
        try:
            completed = subprocess.run(
                [
                    "curl",
                    "-L",
                    "--silent",
                    "--show-error",
                    "--fail",
                    "--max-time",
                    "90",
                    "-A",
                    "Mozilla/5.0 (compatible; CodexMigration/1.0)",
                    "-H",
                    "Accept: */*",
                    url,
                ],
                check=True,
                capture_output=True,
            )
            if completed.stdout:
                return completed.stdout, None
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            last_error = exc

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; CodexMigration/1.0)",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type")
                return data, content_type
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
    raise RuntimeError(f"Failed to download IPFS object {ipfs_hash}") from last_error


def ensure_attachment(
    ipfs_hash: str,
    source_dir: Path | None,
    target_dir: Path,
    download_missing: bool = True,
) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)

    if source_dir and source_dir.is_dir():
        for candidate in sorted(source_dir.iterdir()):
            if not candidate.is_file():
                continue
            if candidate.name == ipfs_hash or candidate.name.startswith(f"{ipfs_hash}."):
                target_name = candidate.name
                if candidate.suffix:
                    shutil.copy2(candidate, target_dir / target_name)
                    return target_name
                extension = detect_image_extension(path=candidate)
                if extension:
                    target_name = f"{ipfs_hash}{extension}"
                shutil.copy2(candidate, target_dir / target_name)
                return target_name

    if not download_missing:
        raise RuntimeError(f"Attachment {ipfs_hash} is not available locally")

    data, content_type = download_ipfs(ipfs_hash)
    extension = detect_image_extension(data=data, content_type=content_type) or ""
    target_name = f"{ipfs_hash}{extension}" if extension else ipfs_hash
    with (target_dir / target_name).open("wb") as fh:
        fh.write(data)
    return target_name


def render_note(
    note: dict,
    notes_markdown_root: Path,
    output_root: Path,
    download_missing: bool = True,
) -> Path:
    content = note["metadata"]["content"]
    character_id = int(note["characterId"])
    note_id = int(note["noteId"])
    slug = slug_from_note(note)
    title = content["title"]
    note_dir = output_root / slug
    attachments_dir = note_dir / "attachments"
    note_dir.mkdir(parents=True, exist_ok=True)

    source_attachments = attachment_source_dir(notes_markdown_root, character_id, note_id)
    attachment_hashes = extract_ipfs_hashes(content.get("content", ""))
    cover_attachments = content.get("attachments", [])
    for attachment in cover_attachments:
        address = str(attachment.get("address", ""))
        if address.startswith("ipfs://"):
            attachment_hashes.append(address.removeprefix("ipfs://"))
    attachment_hashes = list(dict.fromkeys(attachment_hashes))

    resolved_attachments: dict[str, str] = {}
    for ipfs_hash in attachment_hashes:
        try:
            filename = ensure_attachment(
                ipfs_hash,
                source_attachments,
                attachments_dir,
                download_missing=download_missing,
            )
            resolved_attachments[ipfs_hash] = f"./attachments/{filename}"
        except RuntimeError:
            resolved_attachments[ipfs_hash] = unresolved_image_marker(ipfs_hash)

    body = normalize_body(title, content.get("content", ""))
    body = rewrite_ipfs_urls(body, resolved_attachments)
    body = normalize_html_images(body)

    front_matter = build_front_matter(
        {
            "title": title,
            "date": content["date_published"],
            "slug": slug,
            "summary": content.get("summary", ""),
            "tags": content.get("tags", []),
        }
    )

    index_md = note_dir / "index.md"
    with index_md.open("w", encoding="utf-8") as fh:
        fh.write(front_matter)
        fh.write("\n\n")
        if body:
            fh.write(body)
            fh.write("\n")
    return index_md


def migrate_character_33276(
    notes_root: Path,
    notes_markdown_root: Path,
    output_root: Path,
    note_ids: set[int] | None = None,
    download_missing: bool = True,
) -> list[Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    note_paths = sorted(notes_root.glob("*.json"), key=lambda path: int(path.stem.split("-")[-1]))
    for note_path in note_paths:
        note = load_note(note_path)
        if note_ids and int(note["noteId"]) not in note_ids:
            continue
        generated.append(
            render_note(
                note,
                notes_markdown_root,
                output_root,
                download_missing=download_missing,
            )
        )
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate character-33276 notes into Hugo content bundles.")
    parser.add_argument("--notes-root", type=Path, default=Path("character-33276/notes"))
    parser.add_argument("--notes-markdown-root", type=Path, default=Path("character-33276/notes-markdown"))
    parser.add_argument("--output-root", type=Path, default=Path("content/posts"))
    parser.add_argument("--note-id", type=int, action="append", dest="note_ids")
    parser.add_argument("--no-download-missing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    note_ids = set(args.note_ids) if args.note_ids else None
    migrate_character_33276(
        args.notes_root,
        args.notes_markdown_root,
        args.output_root,
        note_ids=note_ids,
        download_missing=not args.no_download_missing,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
