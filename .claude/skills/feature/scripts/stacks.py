"""Stack registry, outline libs/usage/views, version drift and dependency-health verdicts."""

from __future__ import annotations

import argparse
import contextlib
import html
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

STACKS_DIR = Path(".claude/stacks")
REGISTRY = STACKS_DIR / "README.md"
# Researched rows from earlier projects (synced by playbook-sync); `bootstrap` reuses them.
CATALOG = STACKS_DIR / "catalog.md"
STANDARDS = Path(".claude/skills/feature/standards.md")
VERSION_SOURCES = ("uv.lock:", "pnpm-lock:", "compose:", "tool:")
UTILITY = "none (utility)"
REGISTRY_CELLS = 8

# Outline schema (.claude/rules/stacks.md): lib/ + usage/<stack>.yaml -> view/<stack>.md.
LIB_DIR = STACKS_DIR / "lib"
USAGE_DIR = STACKS_DIR / "usage"
VIEW_DIR = STACKS_DIR / "view"
AI_TOOLING = "AI tooling"
LEVELS = frozenset({"basic", "intermediate", "advanced"})
STATUSES = ("used", "candidate", "n/a", "deprecated")
BADGES = {
    "used": "✅ used",
    "candidate": "💡 candidate",
    "n/a": "⛔ n/a",
    "deprecated": "⚠️ deprecated",
}
UNASSESSED = "—"
LIB_REQUIRED = ("stack", "version", "docs_base", "source", "fetched", "verified", "toc", "groups")
LIB_OPTIONAL = ("docs_bases", "skipped")
TOC_REQUIRED = ("index", "match")
TOC_OPTIONAL = ("exclude", "why", "base")
SKIP_KEYS = ("page", "why")
GROUP_KEYS = ("title", "sections")
SECTION_KEYS = ("id", "title", "level", "requires", "ref", "entries")
ENTRY_REQUIRED = ("id", "name", "summary", "lenses", "ref")
ENTRY_OPTIONAL = (
    "import",
    "signature",
    "params",
    "options",
    "returns",
    "since",
    "deprecated",
    "notes",
)
PARAM_REQUIRED = ("name", "type", "desc")
MAX_SUMMARY = 140
MAX_USAGE_TEXT = 160  # usage notes only; lib text and file length are uncapped
STALE_DAYS = 90
_PLANNED = re.compile(r"\s*(planned|plan to|will |to be |should also)", re.I)
_FENCE = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_BASE = re.compile(r"https://\S*[^/\s]")
_URL = re.compile(r"https://\S+")
_REF = re.compile(r"/\S*|https://\S+|mcp:[\w.-]+/\S+")
_REF_BASE = re.compile(r"([a-z0-9-]+):/\S*")
_REPO_PATH = re.compile(r"(^|\s)(src|web|tests|gateways|\.claude)/")
# ToC coverage: links in an index (absolute, markdown-relative, href) and GitHub tree paths.
_LINK = re.compile(r"https?://[^\s)\]\"'<>`]+|\]\((/[^)\s]+)\)|href=\"([^\"#][^\"]*)\"")
_TREE_PATH = re.compile(r'"path":\s*"([^"]+)"')
_PAGE_SUFFIX = re.compile(r"(/index)?(\.mdx?|\.html?)?$")
MCP_URLS = {
    "docs-langchain": "https://docs.langchain.com",
    "reference-langchain": "https://reference.langchain.com",
}

# Health gates (spec F3; thresholds A1/A2).
MIN_AGE_DAYS = 365
MAX_IDLE_DAYS = 183
HEALTH_STALE_DAYS = 365
MIN_MAINTAINERS = 3
MIN_MONTHLY = {"pypi": 50_000, "npm": 100_000}
GATES = (
    "young",
    "idle",
    "archived",
    "deprecated",
    "maintainers",
    "major",
    "downloads",
    "license",
)
STACK_ORGS = frozenset(
    {
        "langchain-ai",
        "vercel",
        "facebook",
        "assistant-ui",
        "shadcn-ui",
        "radix-ui",
        "tailwindlabs",
        "motiondivision",
        "pmndrs",
        "vitest-dev",
        "testing-library",
        "eslint",
        "prettier",
        "microsoft",
        "astral-sh",
        "python",
        "pytest-dev",
        "encode",
        "yaml",
        "pypa",
        "openai",
        "anthropics",
    }
)
PERMISSIVE = frozenset(
    s.lower()
    for s in (
        "MIT",
        "MIT-0",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
        "Zlib",
        "PSF-2.0",
        "Python-2.0",
        "BlueOak-1.0.0",
        "CC0-1.0",
        "BSL-1.0",
    )
)
COPYLEFT_PREFIXES = ("gpl", "lgpl", "agpl", "mpl", "epl", "cddl", "sspl", "eupl", "osl", "busl")
NON_PERMISSIVE = frozenset({"unlicensed", "proprietary", "commercial"})
LICENSE_ALIASES = {
    "mit license": "MIT",
    "the mit license": "MIT",
    "apache software license": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "bsd license": "BSD-3-Clause",
    "bsd": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "isc license": "ISC",
    "psf": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
}
_GITHUB = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[/#?].*)?$")
_SHORTHAND = re.compile(r"(?:github:)?([\w.-]+)/([\w.-]+?)(?:\.git)?(?:#.*)?")
_NOT_OWNERS = frozenset({"sponsors", "orgs", "users", "features", "marketplace"})


@dataclass(frozen=True)
class Row:
    """One registry row of `.claude/stacks/README.md` › `## Stacks` (Python names canonical)."""

    stack: str
    packages: tuple[str, ...]
    version: str
    docs: str
    outline: str | None
    ai_tooling: tuple[str, ...]
    choke: tuple[str, str] | None
    health: str
    line: int


@dataclass(frozen=True)
class Facts:
    """Normalised registry + GitHub health facts for one package; None = unknown."""

    ecosystem: str
    name: str
    version: str | None
    first_release: date | None
    last_release: date | None
    archived: bool | None
    deprecated: bool | None
    license: str | None
    downloads: int | None
    repo: str | None
    owner_type: str | None
    maintainers: int | None

    def to_json(self) -> dict[str, object]:
        """JSON-safe dict (dates as ISO strings)."""
        return {k: v.isoformat() if isinstance(v, date) else v for k, v in asdict(self).items()}

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Facts:
        """Inverse of `to_json`; wrong-typed values become None (unknown)."""
        return cls(
            ecosystem=_str(data.get("ecosystem")) or "",
            name=_str(data.get("name")) or "",
            version=_str(data.get("version")),
            first_release=_date(data.get("first_release")),
            last_release=_date(data.get("last_release")),
            archived=_bool(data.get("archived")),
            deprecated=_bool(data.get("deprecated")),
            license=_str(data.get("license")),
            downloads=_int(data.get("downloads")),
            repo=_str(data.get("repo")),
            owner_type=_str(data.get("owner_type")),
            maintainers=_int(data.get("maintainers")),
        )


# --- typed accessors (yaml/json results are untyped; nothing below escapes as Any) ---


def _dict(value: object) -> dict[str, object]:
    return {str(k): v for k, v in value.items()} if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _mapping(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{where}: expected a mapping")
    return _dict(value)


_BASE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class _Loader(_BASE_LOADER):  # type: ignore[misc,valid-type]
    """Safe loader that rejects duplicate mapping keys (YAML 1.2; PyYAML keeps the last)."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[object, object]:
        """Mapping of `node`; ConstructorError on a repeated key (merge `<<` keys exempt)."""
        seen: set[object] = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                line = key_node.start_mark.line + 1
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r} (line {line})", key_node.start_mark
                )
            seen.add(key)
        mapping: dict[object, object] = super().construct_mapping(node, deep=deep)
        return mapping


_LOADER = _Loader


def _yaml(text: str) -> object:
    loaded: object = yaml.load(text, Loader=_LOADER)
    return loaded


# --- registry and lockfiles ---


def frontmatter(text: str) -> dict[str, object]:
    """YAML frontmatter between leading `---` fences; {} if none, ValueError if invalid."""
    match = _FENCE.match(text)
    if not match:
        return {}
    try:
        data = _yaml(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}".splitlines()[0]) from exc
    if data is None:
        return {}
    return _mapping(data, "frontmatter")


def registry(root: Path) -> list[Row]:
    """Parse the `## Stacks` table; ValueError("<path>:<line>: …") on malformed rows."""
    return _table_rows(root, REGISTRY)


def _table_rows(root: Path, rel: Path) -> list[Row]:
    """Rows of the `## Stacks` table in `rel` (registry or catalog)."""
    path = root / rel
    rows: list[Row] = []
    in_section = False
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if line.startswith("## "):
            in_section = line == "## Stacks"
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] == "stack" or set(line) <= {"|", "-", " ", ":"}:
            continue
        rows.append(_row(cells, f"{rel}:{n}", n))
    # An empty table is valid: a fresh project registers stacks as it adopts them (N1 enforces).
    dupes = sorted({r.stack for r in rows if [x.stack for x in rows].count(r.stack) > 1})
    if dupes:
        raise ValueError(f"{rel}: duplicate stacks {', '.join(dupes)}")
    return rows


def _row(cells: list[str], where: str, n: int) -> Row:
    if len(cells) != REGISTRY_CELLS:
        raise ValueError(f"{where}: expected {REGISTRY_CELLS} cells, got {len(cells)}")
    stack, packages, version, docs, outline, tooling, choke, health = cells
    if not version.startswith(VERSION_SOURCES):
        raise ValueError(
            f"{where}: version '{version}' must start with {'|'.join(VERSION_SOURCES)}"
        )
    if outline not in (stack, UTILITY):
        raise ValueError(f"{where}: outline '{outline}' must be '{stack}' or '{UTILITY}'")
    choke_pair: tuple[str, str] | None = None
    if choke != "—":
        imp, arrow, target = choke.partition("→")
        if not arrow or not imp.strip() or not target.strip():
            raise ValueError(f"{where}: choke point '{choke}' must be '<import> → <path>' or '—'")
        choke_pair = (imp.strip(), target.strip())
    return Row(
        stack=stack,
        packages=tuple(
            p if version.startswith(("pnpm-lock:", "compose:")) else canonicalize_name(p)
            for p in (p.strip() for p in packages.split(","))
            if p and p[0] != "("
        ),
        version=version,
        docs=docs,
        outline=None if outline == UTILITY else outline,
        ai_tooling=tuple(t.strip() for t in tooling.split(";") if t.strip()),
        choke=choke_pair,
        health=health,
        line=n,
    )


def lenses(root: Path) -> frozenset[str]:
    """Lens vocabulary from the standards.md `Lenses:` line."""
    for line in (root / STANDARDS).read_text(encoding="utf-8").splitlines():
        if line.startswith("Lenses:"):
            return frozenset(
                t.strip() for t in line.removeprefix("Lenses:").split("·") if t.strip()
            )
    raise ValueError(f"{STANDARDS}: no 'Lenses:' line")


def _requirement_name(spec: str) -> str:
    try:
        return canonicalize_name(Requirement(spec).name)
    except InvalidRequirement as exc:
        raise ValueError(f"pyproject.toml: bad requirement '{spec}'") from exc


PNPM_LOCKS = ("pnpm-lock.yaml", "web/pnpm-lock.yaml")  # monorepo root first, then a web/ app


def pyprojects(root: Path) -> list[Path]:
    """Root pyproject.toml plus uv workspace members (none if the repo has no Python)."""
    top = root / "pyproject.toml"
    if not top.is_file():
        return []
    doc = tomllib.loads(top.read_text(encoding="utf-8"))
    workspace = _dict(_dict(_dict(doc.get("tool")).get("uv")).get("workspace"))
    members = [
        m / "pyproject.toml"
        for pattern in _list(workspace.get("members"))
        if isinstance(pattern, str)
        for m in sorted(root.glob(pattern))
        if (m / "pyproject.toml").is_file()
    ]
    return [top, *members]


def pnpm_lock_path(root: Path) -> Path | None:
    """The repo's pnpm lockfile, if any (see PNPM_LOCKS)."""
    return next((root / p for p in PNPM_LOCKS if (root / p).is_file()), None)


def _workspace_names(root: Path) -> set[str]:
    """Names of this repo's own Python packages (uv workspace members are not deps)."""
    names = set()
    for path in pyprojects(root):
        project = _dict(tomllib.loads(path.read_text(encoding="utf-8")).get("project"))
        name = _str(project.get("name"))
        if name:
            names.add(canonicalize_name(name))
    return names


def declared_by_ecosystem(root: Path) -> dict[str, set[str]]:
    """Declared deps per registry: pypi (every pyproject; canonical), npm (every pnpm importer)."""
    specs: list[object] = []
    for path in pyprojects(root):
        pyproject = tomllib.loads(path.read_text(encoding="utf-8"))
        project = _dict(pyproject.get("project"))
        specs += _list(project.get("dependencies"))
        for group in (
            *_dict(project.get("optional-dependencies")).values(),
            *_dict(pyproject.get("dependency-groups")).values(),
        ):
            specs += _list(group)  # PEP 735 {include-group = …} entries are dicts: skipped below
        specs += _list(_dict(pyproject.get("build-system")).get("requires"))
    npm: set[str] = set()
    if pnpm_lock_path(root):
        for importer in map(_dict, _dict(pnpm_lock(root).get("importers")).values()):
            for key in ("dependencies", "devDependencies"):
                for name, entry in _dict(importer.get(key)).items():
                    version = _str(_dict(entry).get("version")) or ""
                    if not version.startswith(("link:", "workspace:")):
                        npm.add(name)
    pypi = {_requirement_name(s) for s in specs if isinstance(s, str)} - _workspace_names(root)
    return {"pypi": pypi, "npm": npm}


def declared_deps(root: Path) -> set[str]:
    """Every declared dep name (Python names canonical)."""
    return set().union(*declared_by_ecosystem(root).values())


def _uv_packages(root: Path) -> list[dict[str, object]]:
    path = root / "uv.lock"
    if not path.is_file():
        return []
    lock = tomllib.loads(path.read_text(encoding="utf-8"))
    return [
        p
        for p in map(_dict, _list(lock.get("package")))
        if not {"editable", "virtual"} & set(_dict(p.get("source")))
    ]


def _pnpm_name(key: str) -> str:
    at = key.find("@", 1)
    return key if at == -1 else key[:at]


def locked_packages(root: Path) -> set[str]:
    """Every resolved package name: uv.lock (canonical, minus the editable root) + pnpm-lock."""
    names: set[str] = {canonicalize_name(str(p.get("name"))) for p in _uv_packages(root)}
    if pnpm_lock_path(root):
        names |= {_pnpm_name(k) for k in _dict(pnpm_lock(root).get("packages"))}
    return names


def pnpm_lock(root: Path) -> dict[str, object]:
    """The pnpm-lock.yaml document that carries `settings` (the lock has an env doc too)."""
    path = pnpm_lock_path(root)
    if path is None:
        raise ValueError(f"no pnpm lockfile (looked for {', '.join(PNPM_LOCKS)})")
    text = path.read_text(encoding="utf-8")
    docs = [_dict(d) for d in yaml.load_all(text, Loader=_LOADER) if isinstance(d, dict)]
    with_settings = [d for d in docs if "settings" in d]
    if len(with_settings) != 1:
        raise ValueError(
            f"{path.relative_to(root)}: expected 1 doc with settings, got {len(with_settings)}"
        )
    return with_settings[0]


def pnpm_importers(root: Path) -> list[dict[str, object]]:
    """Every importer of the pnpm lock (`.` plus workspace packages such as apps/web)."""
    return [_dict(i) for i in _dict(pnpm_lock(root).get("importers")).values()]


def installed_version(root: Path, source: str) -> str | None:
    """Installed version of a registry `version` source; None for `tool:`; ValueError if unclear."""
    kind, _, name = source.partition(":")
    if kind == "tool":
        return None
    if kind == "uv.lock":
        wanted = canonicalize_name(name)
        found = [
            str(p.get("version"))
            for p in _uv_packages(root)
            if canonicalize_name(str(p.get("name"))) == wanted
        ]
        if len(found) != 1:
            raise ValueError(f"uv.lock: {name} has {len(found)} locked versions {found}")
        return found[0]
    if kind == "pnpm-lock":
        versions = set()
        for importer in pnpm_importers(root):
            for key in ("dependencies", "devDependencies"):
                entry = _dict(importer.get(key)).get(name)
                if entry is not None:
                    version = _str(_dict(entry).get("version")) or ""
                    if not version or ":" in version.split("(")[0]:
                        raise ValueError(f"pnpm-lock: {name} resolves to '{version}' (link/alias)")
                    versions.add(version.split("(")[0])
        if not versions:
            raise ValueError(f"pnpm-lock: {name} is not a direct dependency")
        if len(versions) > 1:
            raise ValueError(f"pnpm-lock: {name} has several direct versions {sorted(versions)}")
        return versions.pop()
    if kind == "compose":
        services = _dict(
            _dict(_yaml((root / "compose.yaml").read_text(encoding="utf-8"))).get("services")
        )
        image = _str(_dict(services.get(name)).get("image"))
        if image is None:
            raise ValueError(f"compose.yaml: service {name} has no image")
        last = image.rsplit("/", 1)[-1]
        _, colon, tag = last.rpartition(":")
        if "${" in image or "@" in last or not colon or not tag:
            raise ValueError(f"compose.yaml: {name} image '{image}' has no plain tag")
        return tag.removeprefix("v")
    raise ValueError(f"unknown version source '{source}'")


# --- outlines: portable lib + project usage -> generated view ---


@dataclass(frozen=True)
class Param:
    """One `params`/`options` item of a lib entry."""

    name: str
    type: str
    default: str | None
    desc: str


@dataclass(frozen=True)
class Entry:
    """One API or concept of a lib section."""

    id: str
    name: str
    summary: str
    lenses: tuple[str, ...]
    ref: str
    import_from: str | None = None
    signature: str | None = None
    params: tuple[Param, ...] = ()
    options: tuple[Param, ...] = ()
    returns: str | None = None
    since: str | None = None
    deprecated: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Section:
    """One lib section: a concept with its level, prerequisites and entries."""

    id: str
    title: str
    level: str
    requires: tuple[str, ...]
    ref: str
    entries: tuple[Entry, ...]


@dataclass(frozen=True)
class Group:
    """One ordered lib group of sections."""

    title: str
    sections: tuple[Section, ...]


@dataclass(frozen=True)
class TocSource:
    """One live docs index whose in-scope pages the lib must cover (`toc` item)."""

    index: str
    match: str
    exclude: str | None = None
    why: str | None = None
    base: str | None = None


@dataclass(frozen=True)
class Skip:
    """An in-scope page left out of the outline on purpose (`skipped` item)."""

    page: str
    why: str


@dataclass(frozen=True)
class Lib:
    """Portable stack knowledge of `lib/<stack>.yaml` (no repo paths or statuses)."""

    stack: str
    version: str
    docs_base: str
    source: str
    fetched: date | None
    verified: date | None
    groups: tuple[Group, ...]
    docs_bases: Mapping[str, str] = field(default_factory=dict)
    toc: tuple[TocSource, ...] = ()
    skipped: tuple[Skip, ...] = ()

    def sections(self) -> Iterator[Section]:
        """Every section in file order."""
        for group in self.groups:
            yield from group.sections

    def entries(self) -> Iterator[Entry]:
        """Every entry in file order."""
        for section in self.sections():
            yield from section.entries


@dataclass(frozen=True)
class Use:
    """This repo's assessment of one lib entry."""

    status: str
    paths: tuple[str, ...] = ()
    note: str | None = None
    why: str | None = None


@dataclass(frozen=True)
class Usage:
    """Project usage of `usage/<stack>.yaml`: entry id -> Use."""

    stack: str
    entries: Mapping[str, Use]


def _strs(value: object) -> tuple[str, ...]:
    return tuple(v for v in _list(value) if isinstance(v, str))


def _rel(path: Path, root: Path) -> Path:
    return path.relative_to(root) if path.is_relative_to(root) else path


def _load(path: Path) -> dict[str, object]:
    try:
        data = _yaml(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: not valid YAML: {exc}".splitlines()[0]) from exc
    return _mapping(data, path.name)


def _param(value: object) -> Param:
    data = _dict(value)
    return Param(
        name=_str(data.get("name")) or "",
        type=_str(data.get("type")) or "",
        default=_str(data.get("default")),
        desc=_str(data.get("desc")) or "",
    )


def _entry(value: object) -> Entry:
    data = _dict(value)
    return Entry(
        id=_str(data.get("id")) or "",
        name=_str(data.get("name")) or "",
        summary=_str(data.get("summary")) or "",
        lenses=_strs(data.get("lenses")),
        ref=_str(data.get("ref")) or "",
        import_from=_str(data.get("import")),
        signature=_str(data.get("signature")),
        params=tuple(map(_param, _list(data.get("params")))),
        options=tuple(map(_param, _list(data.get("options")))),
        returns=_str(data.get("returns")),
        since=_str(data.get("since")),
        deprecated=_str(data.get("deprecated")),
        notes=_strs(data.get("notes")),
    )


def _section(value: object) -> Section:
    data = _dict(value)
    return Section(
        id=_str(data.get("id")) or "",
        title=_str(data.get("title")) or "",
        level=_str(data.get("level")) or "",
        requires=_strs(data.get("requires")),
        ref=_str(data.get("ref")) or "",
        entries=tuple(map(_entry, _list(data.get("entries")))),
    )


def load_lib(path: Path) -> Lib:
    """Typed lib file; ValueError if not a YAML mapping (validate with `validate_lib`)."""
    data = _load(path)
    return Lib(
        stack=_str(data.get("stack")) or "",
        version=_str(data.get("version")) or "",
        docs_base=_str(data.get("docs_base")) or "",
        source=_str(data.get("source")) or "",
        fetched=_date(data.get("fetched")),
        verified=_date(data.get("verified")),
        groups=tuple(
            Group(
                title=_str(_dict(g).get("title")) or "",
                sections=tuple(map(_section, _list(_dict(g).get("sections")))),
            )
            for g in _list(data.get("groups"))
        ),
        docs_bases={k: v for k, v in _dict(data.get("docs_bases")).items() if isinstance(v, str)},
        toc=tuple(
            TocSource(
                index=_str(t.get("index")) or "",
                match=_str(t.get("match")) or "",
                exclude=_str(t.get("exclude")),
                why=_str(t.get("why")),
                base=_str(t.get("base")),
            )
            for t in map(_dict, _list(data.get("toc")))
        ),
        skipped=tuple(
            Skip(page=_str(k.get("page")) or "", why=_str(k.get("why")) or "")
            for k in map(_dict, _list(data.get("skipped")))
        ),
    )


def load_usage(path: Path) -> Usage:
    """Typed usage file; all entries unassessed when the file does not exist."""
    if not path.is_file():
        return Usage(stack=path.stem, entries={})
    data = _load(path)
    return Usage(
        stack=_str(data.get("stack")) or path.stem,
        entries={
            eid: Use(
                status=_str(use.get("status")) or "",
                paths=_strs(use.get("paths")),
                note=_str(use.get("note")),
                why=_str(use.get("why")),
            )
            for eid, use in ((k, _dict(v)) for k, v in _dict(data.get("entries")).items())
        },
    )


def expand_ref(lib: Lib, ref: str) -> str:
    """Absolute link of a ref: `/p` under docs_base, `<base>:/p` via docs_bases, https/mcp as is."""
    if ref.startswith("/"):
        return lib.docs_base + ref
    if ref.startswith(("https://", "mcp:")):
        return ref
    base, colon, rest = ref.partition(":")
    if colon and rest.startswith("/") and base in lib.docs_bases:
        return lib.docs_bases[base] + rest
    raise ValueError(f"{lib.stack}: unresolvable ref '{ref}'")


def _keys(
    data: dict[str, object], required: tuple[str, ...], optional: tuple[str, ...]
) -> list[str]:
    errors = [f"missing key '{k}'" for k in required if data.get(k) is None]
    return errors + [f"unknown key '{k}'" for k in data if k not in required + optional]


def _text(data: dict[str, object], key: str, cap: int | None = None) -> list[str]:
    """`key`, when present and not null, is a non-empty string of at most `cap` chars."""
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, str) or not value:
        return [f"{key} must be a non-empty string (quote it): got {value!r}"]
    return [f"{key} over {cap} chars"] if cap is not None and len(value) > cap else []


def _base_error(key: str, value: object) -> list[str]:
    if isinstance(value, str) and _BASE.fullmatch(value):
        return []
    return [f"{key} must be an https:// URL without a trailing slash: got {value!r}"]


def _ref_error(value: object, bases: dict[str, object]) -> list[str]:
    ref = value if isinstance(value, str) else ""
    if _REF.fullmatch(ref):
        return []
    base = _REF_BASE.fullmatch(ref)
    if base and base.group(1) in bases:
        return []
    return [
        f"bad ref {value!r} (/<path>, https://…, mcp:<server>/<path> or <docs_bases key>:/<path>)"
    ]


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _raw_ids(data: dict[str, object]) -> Iterator[str]:
    for group in map(_dict, _list(data.get("groups"))):
        for section in map(_dict, _list(group.get("sections"))):
            if sid := _str(section.get("id")):
                yield sid
            yield from (
                e for e in (_str(_dict(x).get("id")) for x in _list(section.get("entries"))) if e
            )


def _requires_errors(value: object, ids: set[str], root: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
        return ["requires must be a list of ids ([] for none)"]
    errors = []
    for req in value:
        stack, colon, rid = str(req).rpartition(":")
        if colon:
            other = root / LIB_DIR / f"{stack}.yaml"
            try:
                ok = other.is_file() and rid in set(_raw_ids(_load(other)))
            except ValueError:
                ok = False
        else:
            ok = req in ids
        if not ok:
            errors.append(f"requires '{req}' does not resolve")
    return errors


def _param_errors(value: object, key: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{key} must be a list"]
    errors = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{key}[{i}]: expected a mapping")
            continue
        data = _dict(item)
        msgs = _keys(data, PARAM_REQUIRED, ("default",)) + _text(data, "name") + _text(data, "type")
        msgs += _text(data, "desc")
        if data.get("default") is not None and not isinstance(data["default"], str):
            msgs.append(f"default must be a string or null (quote it): got {data['default']!r}")
        errors += [f"{key}[{i}]: {m}" for m in msgs]
    return errors


def _entry_errors(
    data: dict[str, object], vocab: frozenset[str], bases: dict[str, object]
) -> list[str]:
    errors = _keys(data, ENTRY_REQUIRED, ENTRY_OPTIONAL) + _text(data, "name")
    errors += _text(data, "summary", MAX_SUMMARY) + _text(data, "returns")
    for key in ("import", "signature", "since", "deprecated"):
        errors += _text(data, key)
    if "ref" in data:
        errors += _ref_error(data["ref"], bases)
    tags = data.get("lenses")
    if tags is not None and (not isinstance(tags, list) or not tags):
        errors.append("lenses must be a non-empty list")
    errors += [f"unknown lens '{t}'" for t in _list(tags) if t not in vocab]
    for key in ("params", "options"):
        if data.get(key) is not None:
            errors += _param_errors(data[key], key)
    notes = data.get("notes")
    if notes is not None and not isinstance(notes, list):
        errors.append("notes must be a list")
    for note in _list(notes):
        if not isinstance(note, str) or not note:
            errors.append(f"note must be a non-empty string: got {note!r}")
    return errors


def _id_errors(value: object, seen: set[str]) -> list[str]:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        return [f"id {value!r} is not kebab-case"]
    if value in seen:
        return [f"duplicate id '{value}'"]
    seen.add(value)
    return []


def _regex_error(key: str, value: object) -> list[str]:
    try:
        re.compile(value if isinstance(value, str) else "(")
    except re.error:
        return [f"{key} must be a valid regex: got {value!r}"]
    return []


def _toc_errors(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        return ["toc must be a non-empty list of {index, match} live doc indexes"]
    errors = []
    for i, item in enumerate(value):
        data = _dict(item)
        msgs = _keys(data, TOC_REQUIRED, TOC_OPTIONAL) + _text(data, "why")
        index = data.get("index")
        if index is not None and not (isinstance(index, str) and _URL.fullmatch(index)):
            msgs.append(f"index must be an https:// URL: got {index!r}")
        msgs += _regex_error("match", data.get("match"))
        if "exclude" in data:
            msgs += _regex_error("exclude", data["exclude"])
            msgs += [] if data.get("why") else ["exclude needs why"]
        if "base" in data:
            msgs += _base_error("base", data["base"])
        errors += [f"toc[{i}]: {m}" for m in msgs]
    return errors


def _skip_errors(value: object, bases: dict[str, object]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return ["skipped must be a list of {page, why}"]
    errors = []
    for i, item in enumerate(value):
        data = _dict(item)
        msgs = _keys(data, SKIP_KEYS, ()) + _text(data, "why")
        if "page" in data:
            msgs += _ref_error(data["page"], bases)
        errors += [f"skipped[{i}]: {m}" for m in msgs]
    return errors


def _top_errors(data: dict[str, object], path: Path) -> list[str]:
    errors = _keys(data, LIB_REQUIRED, LIB_OPTIONAL)
    if data.get("stack") is not None and data["stack"] != path.stem:
        errors.append(f"stack {data['stack']!r} does not match file name '{path.stem}'")
    if data.get("version") is not None and not isinstance(data["version"], str):
        errors.append(f"version must be a string (quote the version): got {data['version']!r}")
    if data.get("docs_base") is not None:
        errors += _base_error("docs_base", data["docs_base"])
    if "docs_bases" in data:
        if not isinstance(data["docs_bases"], dict):
            errors.append("docs_bases must be a mapping of name -> https base")
        for name, base in _dict(data["docs_bases"]).items():
            if not _ID.fullmatch(name) or name in ("https", "mcp"):
                errors.append(f"docs_bases key '{name}' must be kebab-case, not https/mcp")
            errors += _base_error(f"docs_bases.{name}", base)
    errors += _text(data, "source") + _toc_errors(data.get("toc"))
    errors += _skip_errors(data.get("skipped"), _dict(data.get("docs_bases")))
    for key in ("fetched", "verified"):
        value = data.get(key)
        if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
            errors.append(f"{key} must be a bare ISO date (YYYY-MM-DD, unquoted): got {value!r}")
    errors += [
        f"repo path in portable lib: {s[:60]!r}" for s in _strings(data) if _REPO_PATH.search(s)
    ]
    return errors


def validate_lib(path: Path, *, vocab: frozenset[str], root: Path) -> list[str]:
    """Schema errors of one lib file as "<path>: [<where>: ]<msg>"; [] when valid."""
    rel = _rel(path, root)
    try:
        data = _load(path)
    except ValueError as exc:
        return [f"{rel}: {exc}"]
    errors = [f"{rel}: {m}" for m in _top_errors(data, path)]
    groups = data.get("groups")
    if groups is not None and (not isinstance(groups, list) or not groups):
        errors.append(f"{rel}: groups must be a non-empty list")
    elif groups and _dict(_list(groups)[0]).get("title") != AI_TOOLING:
        errors.append(f"{rel}: groups[0] must be '{AI_TOOLING}'")
    ids, seen = set(_raw_ids(data)), set[str]()
    bases = _dict(data.get("docs_bases"))

    def add(where: str, msgs: list[str]) -> None:
        errors.extend(f"{rel}: {where}: {m}" for m in msgs)

    for gi, group in enumerate(_list(groups)):
        gwhere = f"groups[{gi}]"
        g = _dict(group)
        add(gwhere, _keys(g, GROUP_KEYS, ()) + _text(g, "title"))
        sections = g.get("sections")
        if not isinstance(sections, list) or not sections:
            add(gwhere, ["sections must be a non-empty list"])
            continue
        for si, section in enumerate(sections):
            s = _dict(section)
            swhere = _str(s.get("id")) or f"{gwhere}.sections[{si}]"
            msgs = _id_errors(s.get("id"), seen) + _keys(s, SECTION_KEYS, ()) + _text(s, "title")
            if s.get("level") is not None and s["level"] not in LEVELS:
                msgs.append(f"bad level {s['level']!r} (basic|intermediate|advanced)")
            if "requires" in s:
                msgs += _requires_errors(s["requires"], ids, root)
            if "ref" in s:
                msgs += _ref_error(s["ref"], bases)
            entries = s.get("entries")
            if entries is not None and not isinstance(entries, list):
                msgs.append("entries must be a list")
            add(swhere, msgs)
            for ei, entry in enumerate(_list(entries)):
                e = _dict(entry)
                ewhere = _str(e.get("id")) or f"{swhere}.entries[{ei}]"
                add(ewhere, _id_errors(e.get("id"), seen) + _entry_errors(e, vocab, bases))
    return errors


def validate_usage(path: Path, lib: Lib, root: Path) -> list[str]:
    """Schema errors of one usage file against its lib; paths must be relative and exist."""
    rel = _rel(path, root)
    try:
        data = _load(path)
    except ValueError as exc:
        return [f"{rel}: {exc}"]
    errors = [f"{rel}: {m}" for m in _keys(data, ("stack",), ("entries",))]
    if data.get("stack") is not None and data["stack"] not in (path.stem, lib.stack):
        errors.append(f"{rel}: stack {data['stack']!r} does not match file name '{path.stem}'")
    if data.get("entries") is not None and not isinstance(data["entries"], dict):
        errors.append(f"{rel}: entries must be a mapping of entry id -> usage")
    known = {e.id for e in lib.entries()}
    for eid, raw in _dict(data.get("entries")).items():
        use = _dict(raw)
        msgs = [] if eid in known else [f"unknown entry id (not in lib/{lib.stack}.yaml)"]
        msgs += _keys(use, ("status",), ("paths", "note", "why"))
        msgs += _text(use, "note", MAX_USAGE_TEXT) + _text(use, "why", MAX_USAGE_TEXT)
        status = use.get("status")
        if status is not None and status not in STATUSES:
            msgs.append(f"bad status {status!r} ({'|'.join(STATUSES)})")
        paths = use.get("paths")
        if paths is not None and not (
            isinstance(paths, list) and all(isinstance(p, str) for p in paths)
        ):
            msgs.append("paths must be a list of repo paths")
        msgs += [e for e in (_path_error(p, root) for p in _strs(paths)) if e]
        if status == "used" and not _strs(paths):
            msgs.append("status used needs paths")
        if status == "n/a" and use.get("why") is None:
            msgs.append("status n/a needs why")
        # Usage records what shipped; plans live in .claude/plans until Learn flips them.
        if any(_PLANNED.match(str(use.get(k, ""))) for k in ("note", "why")):
            msgs.append("note says planned: record status at Learn (used + paths) or drop it")
        errors += [f"{rel}: {eid}: {m}" for m in msgs]
    return errors


def _path_error(path: str, root: Path) -> str:
    """'' when `path` is relative, stays under root and exists; else why not."""
    if Path(path).is_absolute() or not (root / path).resolve().is_relative_to(root.resolve()):
        return f"path '{path}' must be relative to the repo root"
    return "" if (root / path).exists() else f"path '{path}' does not exist"


def _code(text: str) -> str:
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _table(head: str, params: tuple[Param, ...]) -> list[str]:
    rows = ["", f"| {head} | type | default | notes |", "|---|---|---|---|"]
    for p in params:
        default = _cell(_code(p.default)) if p.default is not None else "—"
        rows.append(f"| {_cell(p.name)} | {_cell(_code(p.type))} | {default} | {_cell(p.desc)} |")
    return rows


def _badge(use: Use | None) -> str:
    return BADGES[use.status] if use and use.status in BADGES else UNASSESSED


def _details(entry: Entry, use: Use | None) -> list[str]:
    """Collapsible block of an entry's params, returns, notes, usage and deprecation; [] if none."""
    parts: list[tuple[str, list[str]]] = []
    if entry.params or entry.options:
        body = _table("param", entry.params) if entry.params else []
        parts.append(("params", body + (_table("option", entry.options) if entry.options else [])))
    if entry.returns:
        parts.append(("returns", ["", f"**Returns** {entry.returns}"]))
    if entry.notes:
        parts.append(("notes", ["", *(f"- {n}" for n in entry.notes)]))
    here = [", ".join(map(_code, use.paths))] if use and use.paths else []
    here += [x for x in (use.note, use.why) if x] if use else []
    if here:
        parts.append(("here", ["", f"**Here** {' — '.join(here)}"]))
    if entry.deprecated:
        parts.append(("deprecated", ["", f"⚠️ Deprecated: {entry.deprecated}"]))
    if not parts:
        return []
    title = f"<b>{html.escape(entry.name)}</b> — {' · '.join(name for name, _ in parts)}"
    body = [line for _, lines in parts for line in lines]
    return ["", f"<details><summary>{title}</summary>", *body, "", "</details>"]


def _render_section(section: Section, usage: Usage) -> list[str]:
    needs = ", ".join(_code(r) if ":" in r else f"[{r}](#{r})" for r in section.requires)
    out = [
        "",
        f'<a id="{section.id}"></a>**{section.title}** · {section.level} · needs '
        f"{needs or 'none'} · [docs][{section.id}] · [↑ top](#top)",
    ]
    out += ["", "| API | What it does | Lenses | Status | Docs |", "|---|---|---|---|---|"]
    details: list[str] = []
    for e in section.entries:
        use = usage.entries.get(e.id)
        api = _cell(_code(e.signature) if e.signature else e.name)
        cells = (api, _cell(e.summary), ", ".join(e.lenses), _badge(use), f"[↗][{e.id}]")
        out.append(f"| {' | '.join(cells)} |")
        details += _details(e, use)
    return out + details


def render_view(lib: Lib, usage: Usage) -> str:
    """Deterministic markdown view of a lib plus this repo's usage (`view/<stack>.md`)."""
    source = (
        f"<{lib.source}>" if _REF.fullmatch(lib.source) and " " not in lib.source else lib.source
    )
    out = [
        f"<!-- generated by stacks.py view from lib/ + usage/{lib.stack}.yaml; do not edit -->",
        '<a id="top"></a>',
        f"# {lib.stack} v{lib.version} · verified {lib.verified} · source {source}",
        "Legend: " + " ".join([*BADGES.values(), f"{UNASSESSED} unassessed"]),
        "",
        "| # | Group | Sections | Entries | ✅ | 💡 |",
        "|---|---|---|---|---|---|",
    ]
    for n, group in enumerate(lib.groups):
        statuses = [_badge(usage.entries.get(e.id)) for s in group.sections for e in s.entries]
        used, candidate = statuses.count(BADGES["used"]), statuses.count(BADGES["candidate"])
        sections = " · ".join(f"[{_cell(s.title)}](#{s.id})" for s in group.sections)
        title = f"[{_cell(group.title)}](#group-{n})"
        out.append(f"| {n} | {title} | {sections} | {len(statuses)} | {used} | {candidate} |")
    links: dict[str, str] = {}
    for n, group in enumerate(lib.groups):
        out += ["", f'## <a id="group-{n}"></a>{n} {group.title}']
        for section in group.sections:
            links[section.id] = _expand_or_raw(lib, section.ref)
            links |= {e.id: _expand_or_raw(lib, e.ref) for e in section.entries}
            out += _render_section(section, usage)
    out += ["", *(f"[{i}]: {links[i]}" for i in sorted(links))]
    return "\n".join(out) + "\n"


def _expand_or_raw(lib: Lib, ref: str) -> str:
    try:
        return expand_ref(lib, ref)
    except ValueError:
        return ref


def libs(root: Path) -> list[Path]:
    """Every lib file under `.claude/stacks/lib/`."""
    return sorted((root / LIB_DIR).glob("*.yaml"))


def validate_all(root: Path) -> list[str]:
    """Errors of every lib and usage file, plus usage files without a lib."""
    known = lenses(root)
    errors: list[str] = []
    names: set[str] = set()
    for path in libs(root):
        names.add(path.stem)
        errors += validate_lib(path, vocab=known, root=root)
        usage = root / USAGE_DIR / path.name
        if usage.is_file():
            with contextlib.suppress(ValueError):  # the lib error above already reports it
                errors += validate_usage(usage, load_lib(path), root)
    return errors + [
        f"{USAGE_DIR}/{p.name}: no lib/{p.name}"
        for p in sorted((root / USAGE_DIR).glob("*.yaml"))
        if p.stem not in names
    ]


def sync_views(root: Path, names: Iterable[str] = (), *, check: bool = False) -> list[str]:
    """Regenerate `view/<stack>.md` for all libs or `names`; `check` reports stale/orphan views."""
    names = list(names)
    # Default: stacks this repo registers. Unregistered libs are shared knowledge from the
    # template (kept for future use), so they get no view until a registry row adopts them.
    registered = {r.outline for r in registry(root) if r.outline}
    wanted = names or [p.stem for p in libs(root) if p.stem in registered]
    messages = []
    for name in wanted:
        try:  # one broken lib must not hide the others
            lib = load_lib(root / LIB_DIR / f"{name}.yaml")
            text = render_view(lib, load_usage(root / USAGE_DIR / f"{name}.yaml"))
        except ValueError as exc:
            messages.append(f"{LIB_DIR}/{name}.yaml: {exc}")
            continue
        out = root / VIEW_DIR / f"{name}.md"
        if out.is_file() and out.read_text(encoding="utf-8") == text:
            continue
        if check:
            messages.append(f"{VIEW_DIR}/{name}.md is stale: run stacks.py view {name}")
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            messages.append(f"wrote {VIEW_DIR}/{name}.md")
    if check and not names:
        messages += [
            f"{VIEW_DIR}/{p.name} has no lib: delete it"
            for p in sorted((root / VIEW_DIR).glob("*.md"))
            if p.stem not in wanted
        ]
    return messages


def refs(root: Path) -> list[tuple[str, str]]:
    """(`<lib path>:<id>`, expanded URL) for every section and entry ref in all libs."""
    found: list[tuple[str, str]] = []
    for path in libs(root):
        try:  # a broken lib is reported by validate; keep checking the others
            lib, rel = load_lib(path), _rel(path, root)
        except ValueError:
            continue
        nodes: list[Section | Entry] = [*lib.sections(), *lib.entries()]
        for node in nodes:
            with contextlib.suppress(ValueError):  # unresolvable ref: validate reports it
                found.append((f"{rel}:{node.id}", expand_ref(lib, node.ref)))
    return found


def page_key(url: str) -> str:
    """Comparable page identity: host + path, no scheme, query, anchor, index or .md/.html."""
    for server, base in MCP_URLS.items():
        url = url.replace(f"mcp:{server}/", f"{base}/", 1)
    url = re.split(r"[?#]", url, maxsplit=1)[0].rstrip("/.,;:)]>")
    return _PAGE_SUFFIX.sub("", url.split("://", 1)[-1]).rstrip("/")


def toc_pages(source: TocSource, text: str) -> set[str]:
    """Page keys of one fetched index that are in scope (`match`, not `exclude`)."""
    urls = {
        urljoin(source.index, html.unescape(m[1] or m[2] or m[0])) for m in _LINK.finditer(text)
    }
    if source.base:
        urls |= {f"{source.base}/{path}" for path in _TREE_PATH.findall(text)}
    keep, drop = re.compile(source.match), source.exclude and re.compile(source.exclude)
    return {page_key(u) for u in urls if keep.search(u) and not (drop and drop.search(u))}


def coverage(lib: Lib, texts: list[str]) -> tuple[str, list[str]]:
    """Summary and problems: in-scope ToC pages neither referenced nor skipped, stale skips."""
    rel = f"{LIB_DIR}/{lib.stack}.yaml"
    problems = [f"{rel}: toc[{i}] index is empty" for i, t in enumerate(texts) if not t]
    live = set[str]().union(*(toc_pages(s, t) for s, t in zip(lib.toc, texts, strict=True)))
    nodes: list[Section | Entry] = [*lib.sections(), *lib.entries()]
    covered = {page_key(_expand_or_raw(lib, n.ref)) for n in nodes}
    skipped = {page_key(_expand_or_raw(lib, s.page)): s.page for s in lib.skipped}
    missing = sorted(live - covered - skipped.keys())
    problems += [f"{rel}: missing https://{p}" for p in missing]
    problems += [f"{rel}: skipped but referenced {skipped[k]}" for k in skipped if k in covered]
    problems += [f"{rel}: skipped page not in toc {skipped[k]}" for k in skipped if k not in live]
    summary = (
        f"== {lib.stack}: {len(live)} toc pages, {len(live & covered)} covered, "
        f"{len(live & skipped.keys())} skipped, {len(missing)} missing"
    )
    return summary, problems


def drift(root: Path, today: date) -> list[str]:
    """Libs whose version ≠ installed or whose `verified` is older than STALE_DAYS."""
    problems = []
    for row in registry(root):
        if row.outline is None:
            continue
        path = root / LIB_DIR / f"{row.outline}.yaml"
        if not path.is_file():  # lib not written yet: N2 reports it, drift skips it
            continue
        rel = _rel(path, root)
        try:
            lib = load_lib(path)
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        installed = installed_version(root, row.version)
        if installed is not None and lib.version.removeprefix("v") != installed.removeprefix("v"):
            problems.append(f"{rel}: lib version {lib.version!r} ≠ installed {installed}")
        if lib.verified is None:
            problems.append(f"{rel}: verified date missing")
        elif (today - lib.verified).days > STALE_DAYS:
            problems.append(f"{rel}: verified {lib.verified} is over {STALE_DAYS} days old")
    return problems


# --- dependency health facts and verdict ---


def github_repo(urls: Iterable[str]) -> str | None:
    """First `owner/repo` among GitHub URL shapes (https, git+, git:, ssh, github:, shorthand)."""
    for url in urls:
        url = url.strip()
        match = _GITHUB.search(url)
        if match is None and "://" not in url and "@" not in url:
            match = _SHORTHAND.fullmatch(url)
        if match and match.group(1).lower() not in _NOT_OWNERS:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def _repo_facts(repo: dict[str, object] | None) -> tuple[str | None, bool | None]:
    if repo is None:
        return None, None
    return _str(_dict(repo.get("owner")).get("type")), _bool(repo.get("archived"))


def _maintainers(commits: list[object] | None) -> int | None:
    if commits is None:
        return None
    logins = {_str(_dict(_dict(c).get("author")).get("login")) for c in commits}
    return len({x for x in logins if x and not x.endswith("[bot]")})


def _monthly(downloads: dict[str, object] | None, *path: str) -> int | None:
    value: object = downloads
    for key in path:
        value = _dict(value).get(key)
    return _int(value)


def facts_from_pypi(
    simple: dict[str, object],
    project: dict[str, object],
    downloads: dict[str, object] | None,
    repo: dict[str, object] | None,
    commits: list[object] | None,
) -> Facts:
    """Facts from PyPI Simple JSON, /pypi/<pkg>/json, pypistats recent, gh repo + commits."""
    info = _dict(project.get("info"))
    uploads = [_date(_dict(f).get("upload-time")) for f in _list(simple.get("files"))]
    latest = [_date(_dict(f).get("upload_time_iso_8601")) for f in _list(project.get("urls"))]
    first = min((d for d in uploads if d), default=None)
    last = max((d for d in latest if d), default=None)
    status = _str(_dict(simple.get("project-status")).get("status")) if simple else None
    if simple and status is None:
        status = "active"
    urls = [u for u in _dict(info.get("project_urls")).values() if isinstance(u, str)]
    urls += [u for u in (_str(info.get("home_page")),) if u]
    owner_type, repo_archived = _repo_facts(repo)
    pypi_archived = None if status is None else status in ("archived", "quarantined")
    return Facts(
        ecosystem="pypi",
        name=_str(info.get("name")) or _str(simple.get("name")) or "",
        version=_str(info.get("version")),
        first_release=first,
        last_release=last,
        archived=_any_true(pypi_archived, repo_archived),
        deprecated=None if status is None else status == "deprecated",
        license=_str(info.get("license_expression")) or _str(info.get("license")),
        downloads=_monthly(downloads, "data", "last_month"),
        repo=github_repo(urls),
        owner_type=owner_type,
        maintainers=_maintainers(commits),
    )


def _npm_license(meta: dict[str, object]) -> str | None:
    lic = meta.get("license")
    if isinstance(lic, str):
        return lic or None
    if isinstance(lic, dict):
        return _str(_dict(lic).get("type"))
    types = [_str(_dict(x).get("type")) for x in _list(meta.get("licenses"))]
    return " OR ".join(t for t in types if t) or None


def _npm_repo_urls(meta: dict[str, object]) -> list[str]:
    repository = meta.get("repository")
    urls = [repository] if isinstance(repository, str) else [_str(_dict(repository).get("url"))]
    urls += [_str(meta.get("homepage")), _str(_dict(meta.get("bugs")).get("url"))]
    return [u for u in urls if u]


def facts_from_npm(
    packument: dict[str, object],
    downloads: dict[str, object] | None,
    repo: dict[str, object] | None,
    commits: list[object] | None,
) -> Facts:
    """Facts from the full npm packument, npm downloads point, gh repo + commits."""
    times = _dict(packument.get("time"))
    latest = _str(_dict(packument.get("dist-tags")).get("latest"))
    meta = _dict(_dict(packument.get("versions")).get(latest)) if latest else {}
    owner_type, repo_archived = _repo_facts(repo)
    deprecated = None if not meta else bool(meta.get("deprecated"))
    return Facts(
        ecosystem="npm",
        name=_str(packument.get("name")) or "",
        version=latest,
        first_release=_date(times.get("created")),
        last_release=_date(times.get(latest)) if latest else None,
        archived=_any_true(False if packument else None, repo_archived),
        deprecated=deprecated,
        license=_npm_license(meta) or _npm_license(packument),
        downloads=_monthly(downloads, "downloads"),
        repo=github_repo(_npm_repo_urls(meta) + _npm_repo_urls(packument)),
        owner_type=owner_type,
        maintainers=_maintainers(commits),
    )


def _any_true(*values: bool | None) -> bool | None:
    if any(v is True for v in values):
        return True
    return None if any(v is None for v in values) else False


def _license_atom(token: str) -> bool | None:
    tok = token.lower()
    if tok in PERMISSIVE:
        return True
    if tok in NON_PERMISSIVE or tok.startswith(COPYLEFT_PREFIXES):
        return False
    return None


def license_ok(expr: str | None) -> bool | None:
    """Permissive? SPDX OR/AND/WITH/parens + legacy PyPI aliases; None = unmappable."""
    if expr is None or not expr.strip():
        return None
    text = LICENSE_ALIASES.get(expr.strip().lower(), expr.strip())
    tokens: list[str] = re.findall(r"\(|\)|[^\s()]+", text)
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take() -> str:
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom() -> bool | None:
        tok = peek()
        if tok is None or tok in (")", "AND", "OR", "WITH"):
            raise ValueError(tok)
        take()
        if tok == "(":
            value = either()
            if take() != ")":
                raise ValueError(")")
            return value
        if peek() == "WITH":  # exceptions (e.g. LLVM-exception) only widen a license
            take()
            atom()
        return _license_atom(tok.removesuffix("+"))

    def both() -> bool | None:
        values = [atom()]
        while peek() == "AND":
            take()
            values.append(atom())
        if False in values:
            return False
        return None if None in values else True

    def either() -> bool | None:
        values = [both()]
        while peek() == "OR":
            take()
            values.append(both())
        if True in values:
            return True
        return None if None in values else False

    try:
        result = either()
    except (ValueError, IndexError):
        return None
    return result if pos == len(tokens) else None


def _official(facts: Facts) -> bool | None:
    return None if facts.repo is None else facts.repo.split("/")[0].lower() in STACK_ORGS


def verdict(facts: Facts, today: date, *, installed: bool = False) -> list[str]:
    """Failed gates plus `unknown:<gate>` for missing facts; [] == PASS. `installed` = recheck."""
    official = _official(facts)
    checks: dict[str, bool | None] = {}
    first, last = facts.first_release, facts.last_release
    if not installed:
        checks["young"] = None if first is None else (today - first).days < MIN_AGE_DAYS
    idle_limit = HEALTH_STALE_DAYS if installed else MAX_IDLE_DAYS
    checks["idle"] = None if last is None else (today - last).days > idle_limit
    checks["archived"] = facts.archived
    checks["deprecated"] = facts.deprecated
    if facts.owner_type == "Organization":
        checks["maintainers"] = False
    elif facts.owner_type is None or facts.maintainers is None:
        checks["maintainers"] = None
    else:
        checks["maintainers"] = facts.maintainers < MIN_MAINTAINERS
    checks["major"] = _exempt(official, _below_one(facts.version))
    floor = MIN_MONTHLY.get(facts.ecosystem)
    low = None if facts.downloads is None or floor is None else facts.downloads < floor
    checks["downloads"] = _exempt(official, low)
    ok = license_ok(facts.license)
    checks["license"] = None if ok is None else not ok
    return [
        gate if checks[gate] else f"unknown:{gate}"
        for gate in GATES
        if gate in checks and checks[gate] is not False
    ]


def _below_one(version: str | None) -> bool | None:
    if version is None:
        return None
    try:
        return Version(version).major < 1
    except InvalidVersion:
        return None


def _exempt(official: bool | None, failed: bool | None) -> bool | None:
    """Gate failure unless the package is official (owned by a registry stack org)."""
    if failed is False or official is True:
        return False
    if failed is None or official is None:
        return None
    return True


def render(gates: list[str]) -> str:
    """One verdict line: FAIL > REVIEW > WATCHLIST young > PASS."""
    unknown = [g for g in gates if g.startswith("unknown:")]
    failed = [g for g in gates if g not in unknown]
    if [g for g in failed if g != "young"]:
        return "FAIL " + " ".join(failed)
    if unknown:
        return "REVIEW " + " ".join(unknown)
    if failed:
        return "WATCHLIST young"
    return "PASS"


# --- CLI (the only place that reads the clock, cwd, git or files outside `root`) ---


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _read_json(path: Path) -> object:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded


def _opt_dict(value: object) -> dict[str, object] | None:
    return _dict(value) if isinstance(value, dict) else None


def _opt_list(value: object) -> list[object] | None:
    return _list(value) if isinstance(value, list) else None


def _facts_cli(ecosystem: str, raw: Path) -> Facts:
    repo = _opt_dict(_read_json(raw / "repo.json"))
    commits = _opt_list(_read_json(raw / "commits.json"))
    downloads = _opt_dict(_read_json(raw / "downloads.json"))
    if ecosystem == "pypi":
        simple = _dict(_read_json(raw / "simple.json"))
        project = _dict(_read_json(raw / "project.json"))
        return facts_from_pypi(simple, project, downloads, repo, commits)
    return facts_from_npm(_dict(_read_json(raw / "packument.json")), downloads, repo, commits)


def _git_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def _stack_id(name: str) -> str:
    """Registry stack id for a package or npm scope: lowercase kebab-case."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _unwired(root: Path, token: str) -> str:
    """Mark a catalog `mcp:`/`skill:` token as optional (`?`) unless this repo wires/locks it."""
    kind, _, value = token.partition(":")
    if kind == "mcp":
        mcp = root / ".mcp.json"
        servers = _dict(json.loads(mcp.read_text())).get("mcpServers") if mcp.is_file() else {}
        return token if value.split()[0] in _dict(servers) else f"mcp?:{value}"
    if kind == "skill":
        lock = root / "skills-lock.json"
        skills = _dict(json.loads(lock.read_text())).get("skills") if lock.is_file() else {}
        sources = {_str(_dict(v).get("source")) for v in _dict(skills).values()}
        return token if value in sources else f"skill?:{value}"
    return token


def _family(name: str) -> str:
    """Row family: `@scope/x` and `scope` share one; `@types/x` belongs with `x`."""
    if name.startswith("@types/"):
        return _stack_id(name.removeprefix("@types/"))
    return _stack_id(name.split("/")[0])


def bootstrap(root: Path, today: date) -> list[str]:
    """Registry rows for every declared dep without one: catalog stacks first, then utilities.

    Catalog rows keep their docs and AI tooling; the version source, choke point and health
    are this repo's. Leftovers join a row of the same family (npm scope or name), else get one
    row per family, marked to assess.
    """
    by_eco = declared_by_ecosystem(root)
    have = {p for r in registry(root) for p in r.packages}
    todo = {n: eco for eco, names in by_eco.items() for n in names if n not in have}
    source = {"pypi": "uv.lock", "npm": "pnpm-lock"}
    family = {n: _family(n) for n in todo}
    rows: dict[str, dict[str, Any]] = {}
    taken = {r.stack for r in registry(root)}
    catalog = _table_rows(root, CATALOG) if (root / CATALOG).is_file() else []
    for row in catalog:
        hits = sorted(p for p in row.packages if p in todo)
        if not hits or row.stack in taken:
            continue
        # Track the catalog's lead package when declared here, so lib versions stay comparable.
        lead = row.version.partition(":")[2]
        pkg = lead if lead in hits else hits[0]
        # tool:/compose: sources are not lockfile entries (e.g. build backends): keep them.
        version = (
            row.version
            if row.version.startswith(("tool:", "compose:"))
            else f"{source[todo[pkg]]}:{pkg}"
        )
        has_lib = (root / LIB_DIR / f"{row.stack}.yaml").is_file()
        rows[row.stack] = {
            "packages": hits,
            "version": version,
            "docs": row.docs,
            "outline": row.stack if row.outline and has_lib else UTILITY,
            "tooling": "; ".join(_unwired(root, t) for t in row.ai_tooling) or "unassessed",
            "health": f"from catalog {today}; set choke point if gated",
            "families": {family[p] for p in hits},
        }
        taken.add(row.stack)
        for p in hits:
            del todo[p]
    for name in sorted(todo):
        fam, eco = family[name], source[todo[name]]
        home = next(
            (
                k
                for k, r in rows.items()
                if (fam in r["families"] or fam == k) and r["version"].startswith(f"{eco}:")
            ),
            None,
        )
        if home is None:
            home = fam if fam not in taken else f"{fam}-{todo[name]}"
            if home in taken:
                raise ValueError(f"bootstrap: no free stack id for {name}; add its row by hand")
            rows[home] = {
                "packages": [],
                "version": f"{source[todo[name]]}:{name}",
                "docs": "—",
                "outline": UTILITY,
                "tooling": "unassessed",
                "health": f"bootstrap {today}: assess (outline-build or keep utility)",
                "families": {fam},
            }
            taken.add(home)
        rows[home]["packages"].append(name)
    return [
        f"| {stack} | {', '.join(r['packages'])} | {r['version']} | {r['docs']} | {r['outline']} "
        f"| {r['tooling']} | — | {r['health']} |"
        for stack, r in rows.items()
    ]


def write_rows(root: Path, lines: list[str]) -> None:
    """Append rows at the end of the registry's `## Stacks` table."""
    path = root / REGISTRY
    text = path.read_text(encoding="utf-8").splitlines()
    start = text.index("## Stacks")
    end = start + 1
    while end < len(text) and (not text[end].strip() or text[end].startswith("|")):
        end += 1
    while not text[end - 1].startswith("|"):
        end -= 1
    path.write_text("\n".join([*text[:end], *lines, *text[end:]]) + "\n", encoding="utf-8")


def guards(root: Path) -> list[str]:
    """Stack-neutral registry guards N1-N5 (N6/N7 are per-project convention tests)."""
    rows = registry(root)
    errors: list[str] = []
    listed = {p for r in rows for p in r.packages}
    missing = declared_deps(root) - listed
    if missing:
        errors.append(f"N1: add registry rows for {sorted(missing)}")
    exempt = {r.stack for r in rows if r.version.startswith(("compose:", "tool:"))}
    stale = {p for r in rows if r.stack not in exempt for p in r.packages} - locked_packages(root)
    if stale:
        errors.append(f"N1: registry lists packages not in a lockfile: {sorted(stale)}")
    for r in rows:
        if r.outline is not None and not (root / LIB_DIR / f"{r.outline}.yaml").is_file():
            errors.append(f"N2: {r.stack}: build lib/{r.outline}.yaml")
    used = {r.outline for r in rows if r.outline}
    orphans = sorted(p.stem for p in libs(root) if p.stem not in used and _usage_path(root, p.stem))
    if orphans:
        errors.append(f"N2: usage files without a registry row: {orphans}")
    errors += [f"N3: {e}" for e in validate_all(root)]
    errors += [f"N3: {e} (run stacks.py view)" for e in sync_views(root, check=True)]
    mcp_file = root / ".mcp.json"
    mcp_doc = _dict(json.loads(mcp_file.read_text())) if mcp_file.is_file() else {}
    servers = set(_dict(mcp_doc.get("mcpServers")))
    tooling = [t for r in rows for t in r.ai_tooling]
    tokens = {t.removeprefix("mcp:").split()[0] for t in tooling if t.startswith("mcp:")}
    if tokens - servers:
        errors.append(f"N4: mcp: tokens not wired in .mcp.json: {sorted(tokens - servers)}")
    lock_file = root / "skills-lock.json"
    skills = {t.removeprefix("skill:") for t in tooling if t.startswith("skill:")}
    if skills:
        lock = _dict(json.loads(lock_file.read_text())).get("skills") if lock_file.is_file() else {}
        sources = {_str(_dict(v).get("source")) for v in _dict(lock).values()}
        if skills - sources:
            errors.append(f"N5: skill: tokens not in skills-lock.json: {sorted(skills - sources)}")
    return errors


def _usage_path(root: Path, stem: str) -> bool:
    """True if this repo has a usage file for the stack (template libs alone are knowledge)."""
    return (root / LIB_DIR.parent / "usage" / f"{stem}.yaml").is_file()


def main(argv: list[str] | None = None, *, today: date | None = None) -> int:
    """CLI: `stacks.py [--root PATH] <command>`; see `--help` for the subcommands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="repo root (default: git toplevel)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("drift", help="lib version/staleness drift, one line each")
    p_verdict = sub.add_parser("verdict", help="facts JSON on stdin -> PASS|FAIL|REVIEW|WATCHLIST")
    p_verdict.add_argument("--installed", action="store_true", help="recheck of an installed dep")
    p_facts = sub.add_parser("facts", help="normalise raw registry/GitHub JSON into facts JSON")
    p_facts.add_argument("ecosystem", choices=sorted(MIN_MONTHLY))
    p_facts.add_argument("package")
    p_facts.add_argument("--raw", type=Path, required=True, help="dir with the fetched JSON files")
    sub.add_parser("refs", help="every lib ref as '<path>:<id> <expanded url>'")
    sub.add_parser("validate", help="lib + usage schema errors, one line each (exit 1 if any)")
    sub.add_parser("guards", help="registry guards N1-N5, one line each (exit 1 if any)")
    p_boot = sub.add_parser("bootstrap", help="rows for unregistered deps (catalog, then utility)")
    p_boot.add_argument("--write", action="store_true", help="append them to the registry")
    p_view = sub.add_parser("view", help="regenerate view/<stack>.md from lib + usage")
    p_view.add_argument("--check", action="store_true", help="exit 1 if a committed view is stale")
    p_view.add_argument("stacks", nargs="*", help="stacks to render (default: every lib)")
    sub.add_parser("deps", help="declared deps as '<ecosystem> <name>' (health rechecks)")
    p_toc = sub.add_parser("toc", help="lib toc indexes as '<stack> <n> <index url>' (to fetch)")
    p_toc.add_argument("stacks", nargs="*", help="stacks (default: every lib)")
    p_cov = sub.add_parser("coverage", help="fetched toc indexes vs lib refs (exit 1 if gaps)")
    p_cov.add_argument("--raw", type=Path, required=True, help="dir with <stack>.<n>.txt indexes")
    p_cov.add_argument("stacks", nargs="*", help="stacks (default: every lib)")
    p_since = sub.add_parser("since", help="ISO timestamp N days ago (GitHub commits query)")
    p_since.add_argument("--days", type=int, default=180)
    args = parser.parse_args(argv)
    if today is None:
        today = date.today()  # noqa: DTZ011 - the one clock read; library code takes `today`
    try:
        status, lines = _run(args, today)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"stacks.py: {exc}", file=sys.stderr)
        return 2
    if lines:
        print("\n".join(lines))
    return status


def _run(args: argparse.Namespace, today: date) -> tuple[int, list[str]]:
    """Exit status and output lines of one parsed command; git root resolved only if needed."""
    if args.cmd == "verdict":
        facts = Facts.from_json(_dict(json.loads(sys.stdin.read())))
        return 0, [render(verdict(facts, today, installed=args.installed))]
    if args.cmd == "facts":
        facts = _facts_cli(args.ecosystem, args.raw)
        if not facts.name:
            facts = Facts.from_json({**facts.to_json(), "name": args.package})
        return 0, [json.dumps(facts.to_json())]
    if args.cmd == "since":
        return 0, [f"{today - timedelta(days=args.days)}T00:00:00Z"]
    root: Path = args.root or _git_root()
    if args.cmd == "drift":
        return 0, drift(root, today)
    if args.cmd == "deps":
        by_eco = declared_by_ecosystem(root)
        return 0, [f"{eco} {name}" for eco in sorted(by_eco) for name in sorted(by_eco[eco])]
    if args.cmd == "refs":
        return 0, [f"{where} {ref}" for where, ref in refs(root)]
    if args.cmd == "bootstrap":
        rows = bootstrap(root, today)
        if args.write and rows:
            write_rows(root, rows)
        return 0, rows
    if args.cmd == "guards":
        errors = guards(root)
        return (1 if errors else 0), errors
    if args.cmd == "validate":
        errors = validate_all(root)
        return (1 if errors else 0), errors
    missing = [s for s in args.stacks if not (root / LIB_DIR / f"{s}.yaml").is_file()]
    if missing:
        raise ValueError(f"no lib for {', '.join(missing)}")
    chosen = [load_lib(root / LIB_DIR / f"{s}.yaml") for s in args.stacks] or [
        load_lib(p) for p in libs(root)
    ]
    if args.cmd == "toc":
        bad = [t.index for lib in chosen for t in lib.toc if not _URL.fullmatch(t.index)]
        if bad:  # the shell fetches these: only plain https URLs, never flags
            raise ValueError(f"toc index must be an https:// URL: {', '.join(bad)}")
        # file stem, not the editable `stack` field (validate checks they match)
        stems = args.stacks or [p.stem for p in libs(root)]
        return 0, [
            f"{stem} {i} {t.index}"
            for stem, lib in zip(stems, chosen, strict=True)
            for i, t in enumerate(lib.toc)
        ]
    if args.cmd == "coverage":
        lines, failed = [], False
        for stem, lib in zip(args.stacks or [p.stem for p in libs(root)], chosen, strict=True):
            texts = [_read_text(args.raw / f"{stem}.{i}.txt") for i in range(len(lib.toc))]
            summary, problems = coverage(lib, texts)
            lines += [summary, *problems]
            failed = failed or bool(problems)
        return (1 if failed else 0), lines
    messages = sync_views(root, args.stacks, check=args.check)
    return (1 if args.check and messages else 0), messages


if __name__ == "__main__":
    sys.exit(main())
