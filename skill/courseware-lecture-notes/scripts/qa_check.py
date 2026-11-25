# -*- coding: utf-8 -*-
"""
质量闸门：课件讲解稿的确定性校验 + 安全自动修复。

检查范围：
  · 格式与跨页一致性：公式定界符与 LaTeX 环境配对、网页/Word 对齐符、
    小标题前后空行、编号列举是否被揉段、是否复述上页、页码是否连续。
  · 纯程序、零 token；只做能确定的安全修复，软检查只进报告。

用法：
  python qa_check.py 讲解稿.md [讲解稿2.md ...]
  python qa_check.py --fix 讲解稿.md    # 仅修复 ### 空行与页首复述，原地保存
"""
import re
import sys
from collections import Counter

CJK = re.compile(r"[\u4e00-\u9fff]")
PAGE_HEAD = re.compile(r"^## P(\d+)\b", re.M)
REVIEW_HEAD = re.compile(r"^#\s*章末(回顾|总结)", re.M)
BEGIN_ENV = re.compile(r"\\begin\{([A-Za-z*]+)\}")
END_ENV = re.compile(r"\\end\{([A-Za-z*]+)\}")
MATRIX_ENVS = {"matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix",
               "array", "cases", "aligned", "split", "gathered"}

# 用户明确不要的「复述上页」开头——只在页首命中才算，正文顺带提及不查。
RECAPPAT = re.compile(
    r"^(?:[^\n。；]{0,30})?"
    r"(本页接着上一页|承接上页|承接上一页|接上一页|延续上一页|"
    r"在上一页(结论|基础)上|基于上一页|本页是上一页|上一页讲到)"
)
# 把两种 Z 字形说成同一个量的错误表述（用户专门纠正过）。
GLYPH_FALSE = re.compile(r"(排版不同|字形不统一|字形上并不统一|只是排版|"
                         r"两种.{0,6}(指同一个量|是同一个量)|同一个量.{0,6}字形)")


def strip_comments(text):
    """HTML 注释（VERIFY-REPORT）里可能有字面 $$，先剥掉再查公式。"""
    return re.sub(r"<!--[\s\S]*?-->", "", text)


def _pages(text):
    """{页号: 页正文}，按 ## Pn 切。返回 (dict, 是否找到页眉)。"""
    marks = list(PAGE_HEAD.finditer(text))
    if not marks:
        return {}, False
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[int(m.group(1))] = text[m.start():end].strip()
    return out, True


def _body_of(page_text):
    """去掉页眉和 ### 行，取正文，用于查开头复述。"""
    lines = [l for l in page_text.split("\n")
             if not l.startswith("## ") and not l.startswith("### ")]
    return "\n".join(lines).strip()


def check(text, expected_pages=None, recite=True, glyph=True):
    """校验整篇。text 为完整 Markdown。返回结构化报告 dict。

    每条 issue：{level: hard|soft, page: int|None, kind, detail}
    hard = 必须修（会破坏渲染或明确违反硬规则）；soft = 建议，交给人工/模型。
    """
    clean = strip_comments(text)
    issues = []

    def add(level, page, kind, detail):
        issues.append({"level": level, "page": page,
                       "kind": kind, "detail": detail})

    pages, has_head = _pages(clean)
    nums = sorted(pages)
    if has_head:
        dup = [n for n, c in Counter(int(m.group(1)) for m in PAGE_HEAD.finditer(clean)).items() if c > 1]
        if dup:
            add("hard", None, "页码", "重复页号：%s" % dup)
        # 只查连续性，不强制从 1 开始——历史讲义有 P0..P64 这类合法编号。
        step_bad = [b for a, b in zip(nums, nums[1:]) if b != a + 1]
        if step_bad:
            add("hard", None, "页码", "页号不连续，断点在：%s" % step_bad[:20])
        if expected_pages and len(nums) != expected_pages:
            add("hard", None, "页码", "应有 %d 页，实际 %d 页" % (expected_pages, len(nums)))

    reviews = len(REVIEW_HEAD.findall(clean))
    if reviews > 1:
        add("hard", None, "章末回顾", "出现 %d 次章末回顾/总结，应只保留一次" % reviews)

    # 全文级公式配对（对干净正文一次性查，定位到页）
    if clean.count("$$") % 2:
        add("hard", None, "公式", "全文 $$ 定界符为奇数，存在未闭合的独立公式块")
    bg = Counter(BEGIN_ENV.findall(clean))
    en = Counter(END_ENV.findall(clean))
    for env in sorted(set(bg) | set(en)):
        if bg[env] != en[env]:
            add("hard", None, "公式环境", "\\begin{%s}=%d 与 \\end{%s}=%d 不配对" %
                (env, bg[env], env, en[env]))

    targets = pages if pages else {None: clean}
    for pno, body in targets.items():
        # 逐页公式块：中文、对齐符、配对
        chunks = body.split("$$")
        for i in range(1, len(chunks), 2):
            block = chunks[i]
            # \text{中文} / \mathrm{} / \mbox{} 是 LaTeX 合法的文字说明，不算错误
            stripped = re.sub(r"\\(?:text|textrm|mathrm|mbox|textbf|textit)\s*\{[^{}]*\}",
                              "", block)
            if CJK.search(stripped):
                add("hard", pno, "公式含中文", "公式块内出现汉字（Word 数学字体无中文字形）")
            has_matrix = any("\\begin{%s}" % e in block for e in MATRIX_ENVS)
            if "&" in block and not has_matrix:
                add("hard", pno, "公式对齐符", "公式块用了 & 但不在矩阵环境内，Word 会显示成字面量")
        # ### 前后空行
        lines = body.split("\n")
        for i, l in enumerate(lines):
            if l.startswith("### "):
                if i > 0 and lines[i - 1].strip():
                    add("soft", pno, "小标题空行", "「%s」前缺空行" % l[:24])
                if i + 1 < len(lines) and lines[i + 1].strip():
                    add("soft", pno, "小标题空行", "「%s」后缺空行" % l[:24])
        # 编号列举揉段：某 prose 行里 >=3 个编号且含分号
        for l in lines:
            if l.lstrip().startswith(("|", "$$", "#")) or not l.strip():
                continue
            marks = len(re.findall(r"\([ivxlcdm]{1,4}\)|\([1-9]\)|[①②③④⑤⑥]", l))
            if marks >= 3 and "；" in l:
                add("soft", pno, "编号揉段", "同一段含 %d 个编号项且用中文分号相连，应逐条分行" % marks)
        # 页首复述上页
        if recite:
            first = _body_of(body)[:160]
            m = RECAPPAT.match(first)
            if m:
                add("soft" if False else "hard", pno, "复述上页",
                    "页首出现复述上页的开头：「%s」" % m.group(0)[:40])
        # 正/花体矛盾说法
        if glyph:
            for m in GLYPH_FALSE.finditer(body):
                add("soft", pno, "字形表述", "把正体/花体 Z 说成排版差异：「%s」" % m.group(0)[:30])

    hard = [x for x in issues if x["level"] == "hard"]
    by_page = {}
    for x in issues:
        by_page.setdefault(x["page"], []).append(x)
    return {
        "issues": issues, "hard": hard, "by_page": by_page,
        "hard_pages": sorted({x["page"] for x in hard if x["page"] is not None}),
        "ok": not hard, "pages": len(pages),
    }


def fix_format(text):
    """只做确定安全的纯文本修复，返回 (新文本, 改动条数)。不改公式内容/数值。"""
    n = 0
    # 1) ### 前后补空行
    lines = text.split("\n")
    out = []
    for i, l in enumerate(lines):
        if l.startswith("### "):
            if out and out[-1].strip():
                out.append("")
                n += 1
            out.append(l)
            if i + 1 < len(lines) and lines[i + 1].strip():
                out.append("")
                n += 1
        else:
            out.append(l)
    text = "\n".join(out)
    # 2) 删除页首「复述上页」整句。按页眉切片，逐页只处理正文开头，绝不整页重写。
    marks = list(PAGE_HEAD.finditer(text))
    pieces = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        piece = text[m.start():end]
        if i == 0 and m.start() > 0:
            pieces.append(text[:m.start()])       # 标题/前言原样保留
        head_end = piece.find("\n")
        if head_end < 0:
            pieces.append(piece)
            continue
        head, body = piece[:head_end + 1], piece[head_end + 1:]
        lead = body[:200]
        rm = RECAPPAT.match(lead.lstrip())
        if rm:
            tail = lead[lead.find(rm.group(1)):]
            endm = re.search(r"[。；\n]", tail)
            cut = len(lead) - len(tail) + (endm.end() if endm else len(tail))
            body = (lead[cut:] + body[200:]).lstrip("\n")
            n += 1
        if body and not body.startswith("\n"):
            body = "\n" + body       # 页眉后保留一个空行
        pieces.append(head + body)
    if marks:
        text = "".join(pieces)
    else:
        lead = text[:200]
        rm = RECAPPAT.match(lead.lstrip())
        if rm:
            text = re.sub(r"^[^\n。；]*[。；]\s*", "", text, count=1)
            n += 1
    return text, n


def report_text(res, title="讲解稿质检"):
    """人类可读报告。"""
    lines = ["=== %s ===" % title]
    if res["ok"]:
        lines.append("通过：没有发现硬错误（公式闭合、环境配对、页码连续、小标题格式正常）。")
    else:
        lines.append("发现硬错误 %d 条：" % len(res["hard"]))
        for x in res["hard"]:
            lines.append("  [P%s] %s：%s" % (x["page"] or "全篇", x["kind"], x["detail"]))
    soft = [x for x in res["issues"] if x["level"] == "soft"]
    if soft:
        lines.append("建议 %d 条：" % len(soft))
        for x in soft[:40]:
            lines.append("  [P%s] %s：%s" % (x["page"] or "全篇", x["kind"], x["detail"]))
        if len(soft) > 40:
            lines.append("  ...另有 %d 条" % (len(soft) - 40))
    if res.get("hard_pages"):
        lines.append("需定点重写的页：%s" % res["hard_pages"])
    return "\n".join(lines)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法：python qa_check.py 讲解稿.md [更多.md ...]")
        print("      python qa_check.py --fix 讲解稿.md   # 仅自动修复安全项并原地保存")
        return 0
    do_fix = "--fix" in argv
    files = [a for a in argv if a != "--fix"]
    worst = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if do_fix:
            fixed, n = fix_format(text)
            if n:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                print("%s：自动修复 %d 处（### 空行 / 页首复述），已原地保存。" % (path, n))
                text = fixed
        res = check(text)
        print(report_text(res, path))
        worst = max(worst, 1 if res["hard"] else 0)
        print()
    return worst


if __name__ == "__main__":
    sys.exit(main())
