#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成课件讲解模板。

输入 PDF（首选）或已渲染的页面图片目录，输出：
  · sources/                原始 PDF 与逐页截图（模板引用相对路径）
  · <名字>_讲解模板.md      或 <名字>_笔记模板.md

用法：
  python scripts/build_template.py --input 课件.pdf --out 课件_讲解模板.md
  python scripts/build_template.py --input 课件.pdf --out 课件_笔记模板.md --kind note
  python scripts/build_template.py --images 页面目录 --out 课件_讲解模板.md
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from headings import scan

SKILL_ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = SKILL_ROOT / "references"

DEPTHS = {
    "brief": ("简明", 260),
    "standard": ("标准", 620),
    "deep": ("深入", 900),
    "max": ("极致", 1400),
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def _title_from(path: Path) -> str:
    stem = path.stem if path.is_file() else path.name
    stem = re.sub(r"_(讲解模板|笔记模板|讲解|笔记)$", "", stem)
    return stem or "课件"


def _copy_image(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)


def _read_sidecar(image: Path) -> str:
    for ext in (".txt", ".md"):
        side = image.with_suffix(ext)
        if side.is_file():
            return side.read_text(encoding="utf-8", errors="replace")
    return ""


def collect_pdf(pdf: Path, out_dir: Path):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # type: ignore

    src_dir = out_dir / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    saved_pdf = src_dir / pdf.name
    if pdf.resolve() != saved_pdf.resolve():
        shutil.copy2(pdf, saved_pdf)

    pages_dir = src_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    doc = fitz.open(str(pdf))
    try:
        total = len(doc)
        for i, page in enumerate(doc, start=1):
            image = pages_dir / ("page_%d.png" % i)
            pix = page.get_pixmap(dpi=150, alpha=False)
            pix.save(str(image))
            text = page.get_text("text") or ""
            pages.append({
                "page": i,
                "img": image.relative_to(out_dir).as_posix(),
                "text": text,
                "headings": [h["label"] for h in scan(text)],
            })
    finally:
        doc.close()
    material = ["- 原始课件：`%s`" % saved_pdf.relative_to(out_dir).as_posix()]
    material += ["- 逐页截图：`sources/pages/page_{n}.png`（Pn → 第 n 张，共 %d 张）" % total]
    return pages, material


def collect_images(image_dir: Path, out_dir: Path):
    files = sorted([p for p in image_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTS], key=_natural_key)
    if not files:
        raise SystemExit("图片目录里没有可用的页面图片：%s" % image_dir)
    pages_dir = out_dir / "sources" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for i, src in enumerate(files, start=1):
        ext = ".png" if src.suffix.lower() == ".png" else src.suffix.lower()
        dst = pages_dir / ("page_%d%s" % (i, ext))
        _copy_image(src, dst)
        text = _read_sidecar(src)
        pages.append({
            "page": i,
            "img": dst.relative_to(out_dir).as_posix(),
            "text": text,
            "headings": [h["label"] for h in scan(text)],
        })
    material = ["- 逐页截图：`sources/pages/page_{n}.%s`（Pn → 第 n 张，共 %d 张）"
                % (pages[0]["img"].rsplit(".", 1)[-1], len(pages))]
    return pages, material


def load_spec(kind: str, min_chars: int, glossary: str) -> str:
    spec_path = SPEC_DIR / ("notes-spec.md" if kind == "note" else "lecture-spec.md")
    spec = spec_path.read_text(encoding="utf-8").replace("{{MIN_CHARS}}", str(min_chars))
    # 参考文件为了可读性带了一级标题；嵌进模板时只保留规范正文
    marker = "## 笔记规范" if kind == "note" else "## 讲解规范"
    if marker in spec:
        spec = spec[spec.find(marker):]
    if not glossary.strip():
        return spec
    block = ("**术语表 · 本课统一用法** — 以下译名与符号必须沿用，"
             "不要自己另起一套；同义写法也往这里靠：\n\n%s\n\n" % glossary.strip())
    if kind == "note":
        return spec.rstrip() + "\n\n" + block
    marker = "**交稿前自检"
    if marker in spec:
        return spec.replace(marker, block + marker, 1)
    return spec.rstrip() + "\n\n" + block


def build(title: str, pages, material, out: Path, kind: str, min_chars: int,
          glossary: str):
    out.parent.mkdir(parents=True, exist_ok=True)
    spec = load_spec(kind, min_chars, glossary)
    placeholder = "**【本页笔记】**" if kind == "note" else "**【逐页讲解】**"

    lines = ["# 《%s》" % title, ""]
    if material:
        lines += ["材料（自己按需读取）："] + material + [""]
    lines += [spec.rstrip(), ""]

    for p in pages:
        lines += ["## P%d ｜ 第 %d 页" % (p["page"], p["page"]), ""]
        if p["headings"]:
            lines += ["本页小标题（线索，以截图为准核对）：" +
                      "；".join(p["headings"]), ""]
        lines += [placeholder, ""]

    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="生成课件讲解/笔记模板")
    ap.add_argument("--input", type=Path, help="PDF 文件（PPT 请先导出 PDF）")
    ap.add_argument("--images", type=Path, help="已渲染页面图片目录，按文件名自然排序")
    ap.add_argument("--out", type=Path, required=True, help="输出模板 .md 路径")
    ap.add_argument("--title", default="", help="课件标题；默认取输入文件名")
    ap.add_argument("--kind", choices=["detail", "note"], default="detail")
    ap.add_argument("--depth", choices=list(DEPTHS), default="deep")
    ap.add_argument("--min-chars", type=int, default=0,
                    help="每页篇幅起点；不填时按 --depth 取 260/620/900/1400")
    ap.add_argument("--glossary-file", type=Path, help="术语表文本文件")
    args = ap.parse_args()

    if bool(args.input) == bool(args.images):
        ap.error("--input 和 --images 必须且只能给一个")
    source = args.input or args.images
    title = args.title.strip() or _title_from(source)
    out = args.out.expanduser().resolve()
    out_dir = out.parent

    if args.input:
        if args.input.suffix.lower() != ".pdf":
            ap.error("目前只直接读 PDF；PPT/PPTX 请先另存为 PDF，或导出页面图片后用 --images")
        pages, material = collect_pdf(args.input.resolve(), out_dir)
    else:
        pages, material = collect_images(args.images.resolve(), out_dir)

    min_chars = args.min_chars or DEPTHS[args.depth][1]
    glossary = args.glossary_file.read_text(encoding="utf-8", errors="replace") \
        if args.glossary_file else ""
    build(title, pages, material, out, args.kind, min_chars, glossary)

    print("已生成：%s" % out)
    if args.kind == "note":
        print("页数：%d；模式：复习笔记" % len(pages))
    else:
        print("页数：%d；模式：逐页讲解；篇幅起点：%d 字" % (len(pages), min_chars))
    print("下一步：让 Agent 按模板逐页写，写完运行 scripts/qa_check.py 检查。")


if __name__ == "__main__":
    main()
