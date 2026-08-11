"""Cube modeling service: read/write Cube schema files (cubes/*.js, views/*.yml)."""
import os
import re
from pathlib import Path
from typing import Optional

import yaml

CUBES_DIR = Path(os.environ.get("CUBE_MODEL_CUBES_DIR", r"D:\DataMind\cube\model\cubes"))
VIEWS_DIR = Path(os.environ.get("CUBE_MODEL_VIEWS_DIR", r"D:\DataMind\cube\model\views"))

_CUBE_HEAD = re.compile(r"cube\(\s*`([^`]+)`\s*,\s*\{")
_CUBE_TITLE = re.compile(r"^\s{0,3}title\s*:\s*[\"']([^\"']*)[\"']", re.M)
_SQL_TABLE = re.compile(r"sql_table\s*:\s*`([^`]*)`")
_DATA_SOURCE = re.compile(r"data_source\s*:\s*`([^`]*)`")
_TOP_SQL = re.compile(r"^\s{0,3}sql\s*:\s*`([^`]*)`", re.M)
_SECTION = re.compile(r"^\s*(joins|dimensions|measures|segments)\s*:\s*\{", re.M)
_ENTRY = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\{", re.M)
_SQL_PROP = re.compile(r"sql\s*:\s*`([^`]*)`", re.S)
_TYPE_PROP = re.compile(r"type\s*:\s*`([^`]*)`")
_TITLE_PROP = re.compile(r"title\s*:\s*[\"']([^\"']*)[\"']")
_REL_PROP = re.compile(r"relationship\s*:\s*`([^`]*)`")
_PK_PROP = re.compile(r"primary[_]?[kK]ey\s*:\s*true")


def _brace_block(text: str, start: int) -> tuple[int, int]:
    """Return (start, end) of the balanced { ... } starting at text[start] == '{'."""
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return start, len(text)


def _collapse(sql: str) -> str:
    return re.sub(r"\s+", " ", sql or "").strip()


def parse_cube_file(path: Path) -> Optional[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = _CUBE_HEAD.search(text)
    if not m:
        return None
    name = m.group(1)
    body_start = text.index("{", m.start())
    body_end = _brace_block(text, body_start)[1]
    body = text[body_start:body_end]
    sec_m = _SECTION.search(body)
    title_area = body[: sec_m.start()] if sec_m else body
    ct = _CUBE_TITLE.search(title_area)

    cube: dict = {
        "name": name,
        "title": ct.group(1) if ct else name,
        "sql_table": "",
        "sql": "",
        "data_source": "default",
        "joins": [],
        "dimensions": [],
        "measures": [],
        "segments": [],
    }
    st = _SQL_TABLE.search(body)
    if st:
        cube["sql_table"] = st.group(1)
    ds = _DATA_SOURCE.search(body)
    if ds:
        cube["data_source"] = ds.group(1)
    ts = _TOP_SQL.search(body)
    if ts and not cube["sql_table"]:
        cube["sql"] = _collapse(ts.group(1))

    # split body into sections
    sections: dict[str, str] = {}
    for sm in _SECTION.finditer(body):
        sec_name = sm.group(1)
        sec_start = body.index("{", sm.start())
        sec_end = _brace_block(body, sec_start)[1]
        sections[sec_name] = body[sec_start:sec_end]

    for sec_name, sec in sections.items():
        for em in _ENTRY.finditer(sec):
            entry_name = em.group(1)
            e_start = sec.index("{", em.start())
            e_end = _brace_block(sec, e_start)[1]
            block = sec[e_start:e_end]
            entry: dict = {"name": entry_name}
            sp = _SQL_PROP.search(block)
            if sp:
                entry["sql"] = _collapse(sp.group(1))
            tp = _TYPE_PROP.search(block)
            if tp:
                entry["type"] = tp.group(1)
            tt = _TITLE_PROP.search(block)
            if tt:
                entry["title"] = tt.group(1)
            rp = _REL_PROP.search(block)
            if rp:
                entry["relationship"] = rp.group(1)
            if _PK_PROP.search(block):
                entry["primary_key"] = True
            cube[sec_name].append(entry)
    return cube


def _render_entries(entries: list[dict], fields: list[str]) -> str:
    out = ""
    for e in entries or []:
        name = (e.get("name") or "").strip()
        if not name:
            continue
        lines = [f"    {name}: {{"]
        if e.get("sql"):
            lines.append(f"      sql: `{e['sql']}`,")
        if e.get("type"):
            lines.append(f"      type: `{e['type']}`,")
        if e.get("relationship"):
            lines.append(f"      relationship: `{e['relationship']}`,")
        if e.get("title"):
            lines.append(f'      title: "{e["title"]}",')
        if e.get("primary_key"):
            lines.append("      primary_key: true,")
        lines.append("    },")
        out += "\n" + "\n".join(lines)
    return out


def render_cube_file(cube: dict) -> str:
    name = (cube.get("name") or "").strip()
    if not name:
        raise ValueError("Cube 名称不能为空")
    lines = [f"cube(`{name}`, {{", ""]
    if cube.get("sql_table"):
        lines.append(f"  sql_table: `{cube['sql_table']}`,")
    elif cube.get("sql"):
        lines.append(f"  sql: `{cube['sql']}`,")
    if cube.get("title") and cube.get("title") != cube.get("name"):
        lines.append(f'  title: "{cube["title"]}",')
    lines += [
        "",
        f"  data_source: `{cube.get('data_source') or 'default'}`,"
    ]
    if cube.get("joins"):
        lines += ["", "  joins: {"]
        lines.append(_render_entries(cube["joins"], []).rstrip())
        lines.append("  },")
    if cube.get("dimensions"):
        lines += ["", "  dimensions: {"]
        lines.append(_render_entries(cube["dimensions"], []).rstrip())
        lines.append("  },")
    if cube.get("measures"):
        lines += ["", "  measures: {"]
        lines.append(_render_entries(cube["measures"], []).rstrip())
        lines.append("  },")
    if cube.get("segments"):
        lines += ["", "  segments: {"]
        lines.append(_render_entries(cube["segments"], []).rstrip())
        lines.append("  },")
    lines += ["", "});", ""]
    return "\n".join(lines)


def list_models() -> dict:
    cubes: list[dict] = []
    if CUBES_DIR.is_dir():
        for f in sorted(CUBES_DIR.glob("*.js")):
            cube = parse_cube_file(f)
            if cube:
                cubes.append(cube)

    views: list[dict] = []
    if VIEWS_DIR.is_dir():
        for f in sorted(VIEWS_DIR.glob("*.yml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict) or not isinstance(data.get("views"), list):
                continue
            for v in data["views"]:
                if isinstance(v, dict) and v.get("name"):
                    views.append(v)
    return {"cubes": cubes, "views": views}


def get_cube(name: str) -> Optional[dict]:
    path = CUBES_DIR / f"{name}.js"
    if not path.exists():
        return None
    return parse_cube_file(path)


def save_cube(cube: dict) -> dict:
    name = (cube.get("name") or "").strip()
    if not name:
        raise ValueError("Cube 名称不能为空")
    CUBES_DIR.mkdir(parents=True, exist_ok=True)
    path = CUBES_DIR / f"{name}.js"
    path.write_text(render_cube_file(cube), encoding="utf-8")
    return {"name": name, "file": str(path)}


def delete_cube(name: str) -> bool:
    path = CUBES_DIR / f"{name}.js"
    if not path.exists():
        return False
    path.unlink()
    return True


def save_view(view: dict) -> dict:
    name = (view.get("name") or "").strip()
    if not name:
        raise ValueError("视图名称不能为空")
    VIEWS_DIR.mkdir(parents=True, exist_ok=True)
    # one view per yml file
    data = {"views": [view]}
    path = VIEWS_DIR / f"{name}.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"name": name, "file": str(path)}


def delete_view(name: str) -> bool:
    path = VIEWS_DIR / f"{name}.yml"
    if not path.exists():
        return False
    path.unlink()
    return True


async def refresh_cube() -> dict:
    """Restart the configured Cube container so new schema files are loaded."""
    from app.services.cube_deploy_service import restart_cube_container

    code, out, err = await restart_cube_container()
    if code != 0:
        return {"ok": False, "message": f"重启失败: {(err or out).strip()[:200]}"}
    return {"ok": True, "message": "Cube 已重启，模型已生效"}
