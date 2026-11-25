# -*- coding: utf-8 -*-
"""从课件页文字里认出小标题线索；只给线索，不翻译、不改写。"""
import re

_NUM = (r"(?:\d{1,2}(?:\.\d{1,2}){0,3}"
        r"|[一二三四五六七八九十]{1,3}"
        r"|[（(][一二三四五六七八九十\d]{1,3}[)）])")
NUM_LINE = re.compile(r"^\s*(" + _NUM + r")\s*[.、．:：\-]?\s*(.*)$")
ZH_SECTION = re.compile(
    r"^\s*第\s*([一二三四五六七八九十百零〇\d]{1,4})\s*[节讲部分]\s*[.．:：、\-]?\s*(.*)$")
EN_SECTION = re.compile(
    r"^\s*((?:chapter|section|part|unit|lecture)\s+\d+(?:\.\d+)*)"
    r"[.．:：、\-]?\s*(.*)$", re.I)
SENT_TAIL = re.compile(r"[。！？；，、；.!?;,:：]$")
FORMULAISH = re.compile(r"[=＝{}∑∫]|\\(?:frac|sum|begin|vec|hat)|\$.{0,40}\$")
BAD_HEAD = re.compile(
    r"^(?:page|slide|fig(?:ure)?\.?|tab(?:le)?\.?|example|exercise|"
    r"note|reference|ref\.?|www\.|http)\b", re.I)
CJK = re.compile(r"[\u4e00-\u9fff]")
STYLE_MARK = "§"


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower()).strip(" ·•-—_: ")


def _clean(text):
    text = (text or "").replace("\ufffd", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(ln.strip() for ln in text.split("\n") if ln.strip()).strip()


def looks_head_text(s, max_len=90):
    t = (s or "").strip().lstrip(STYLE_MARK).strip()
    n = len(t)
    if not (2 <= n <= max_len):
        return False
    if SENT_TAIL.search(t) or FORMULAISH.search(t):
        return False
    if BAD_HEAD.match(t) or "http" in t.lower() or "@" in t:
        return False
    if re.fullmatch(r"[\W\d_]+", t):
        return False
    if re.search(r"[。！？；，]", t):
        return False
    if not CJK.search(t):
        words = re.findall(r"[A-Za-z0-9']+", t)
        if len(words) > 14:
            return False
    return True


def _mk(num, text, level):
    label = ("%s %s" % (num, text)).strip()
    return {"num": num, "text": text, "label": label, "level": level}


def scan(text, limit=12):
    """返回本页小标题标签，按版面顺序；认不出来返回空列表。"""
    lines = [ln.strip() for ln in _clean(text).split("\n") if ln.strip()]
    if not lines:
        return []
    out, seen, used = [], set(), set()
    i = 0
    while i < len(lines):
        line = lines[i].lstrip(STYLE_MARK).strip()
        num, rest, level = "", "", 2
        m = NUM_LINE.match(line)
        if m:
            num, rest = m.group(1).strip(), (m.group(2) or "").strip()
            if (re.fullmatch(r"\d{1,2}", num) and rest and CJK.search(rest)
                    and not re.match(r"^\s*" + _NUM + r"\s*[.、．:：\-]", line)):
                num, rest = "", ""
        else:
            m = ZH_SECTION.match(line)
            if m:
                num, rest, level = "第%s节" % m.group(1), (m.group(2) or "").strip(), 1
            else:
                m = EN_SECTION.match(line)
                if m:
                    num, rest, level = m.group(1), (m.group(2) or "").strip(), 1

        if num and not rest:
            if i + 1 < len(lines):
                nxt = lines[i + 1].lstrip(STYLE_MARK).strip()
                if (looks_head_text(nxt) and not NUM_LINE.match(nxt)
                        and not EN_SECTION.match(nxt)):
                    key = _norm(num + " " + nxt)
                    if key not in seen:
                        seen.add(key)
                        out.append(_mk(num, nxt, level))
                    used.add(i)
                    used.add(i + 1)
                    i += 2
                    continue
            i += 1
            continue

        if num and rest and looks_head_text(rest):
            key = _norm(num + " " + rest)
            if key not in seen:
                seen.add(key)
                out.append(_mk(num, rest, level))
            used.add(i)
            i += 1
            continue

        i += 1

    # 封面 / 目录页的短行：只在最上面两行且整页有较多文字时补
    top = min(2, len(lines)) if len(lines) >= 3 else (1 if len(lines) == 2 else 0)
    for j in range(top):
        if j in used:
            continue
        line = lines[j].lstrip(STYLE_MARK).strip()
        if not looks_head_text(line, 48):
            continue
        if NUM_LINE.match(line) or EN_SECTION.match(line):
            continue
        key = _norm(line)
        if key in seen:
            continue
        seen.add(key)
        out.append(_mk("", line, 1))

    out.sort(key=lambda h: (0 if h["level"] == 1 and not h["num"] else 1,))
    return out[:limit]
