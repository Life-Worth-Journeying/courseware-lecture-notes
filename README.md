# 根号M7 课件讲解 Skill

把 PPT / PDF 课件写成逐页中文讲解稿，或写成可以直接抄的复习笔记。

这是「根号M7」桌面软件 **v5.2.0 手动版**的规范和提示词的 Agent Skill 封装：不调用软件 API、不需要 API Key，由当前 AI Agent 自己读取课件、逐页写作，再用脚本做确定性质检。

> 它不是“更强的自动讲解 API”，而是把原本靠复制粘贴的一套课件讲解规范，变成可安装、可版本管理、可分享给其他 Agent 的 Skill。

## 它解决什么

- 逐页讲解：先认小标题，再按版面顺序讲；公式、符号、上下标、条件零删减；补推导、讲物理意义、标易错点。
- 复习笔记：只留定义、结论、适用条件、步骤、对比和易错点，不写导入、过渡和解题表演。
- 交稿质量：强制写 `VERIFY-REPORT`，跑程序化质检，整篇定名，保留页码和 `## Pn` 骨架。
- 可复现：规范、提示词、模板生成和质检都在仓库里，不依赖某个网页对话的上下文。

## 和软件里的“手动模式”怎么选

| | 软件手动模式 | 这个 Skill |
|---|---|---|
| 谁读课件 | 豆包 / WorkBuddy 等外部模型 | 当前 Agent |
| 操作方式 | 生成模板 → 复制路径和提示词 → 粘贴 → 导回 | 一句话触发，Agent 自动建模板、读课件、写稿、质检 |
| 适合 | 没有 API Key、想人工盯着每一步、用任意网页模型 | 支持本地文件和命令行的 Agent、想批量复用、想发 GitHub |
| 风险 | 复制粘贴易漏步骤，依赖外部模型自觉 | Agent 读图能力决定上限，仍需要人工抽查事实 |

**建议：不要二选一。** 保留手动模式作为“透明、可审计、任意模型可用”的兜底；把 Skill 作为“标准化、可分享、可批量”的入口。两者共用同一套规范，成品格式一致。

## 仓库结构

```text
root-m7-courseware-notes/
├── README.md
└── skill/
    └── root-m7-courseware-notes/
        ├── SKILL.md
        ├── references/
        │   ├── lecture-spec.md       # 逐页讲解完整规范
        │   ├── notes-spec.md         # 复习笔记完整规范
        │   └── handoff-prompts.md    # 手动模式提示词备份
        └── scripts/
            ├── build_template.py     # PDF/页面图片 → 讲解/笔记模板
            ├── headings.py           # 小标题线索识别
            └── qa_check.py           # 零 token 程序化质检
```

## 安装

把 `skill/root-m7-courseware-notes` 整个文件夹复制到你使用的 Agent 的 skills 目录。不同客户端的目录不同；只要该客户端支持 Agent Skills，放入其 skills 根目录即可。

安装后不需要背很长的提示词，直接说：

```text
用根号M7规范，把这份 PDF 写成逐页讲解。
```

或：

```text
用根号M7笔记规范，把这份课件写成能直接抄的复习笔记。
```

Agent 会读取 `SKILL.md`，按里面的工作流选择规范、生成模板、逐页写作、跑质检。

## 命令行用法（不经过 Agent 也可以先建模板）

需要 Python 3.10+；PDF 渲染依赖 `PyMuPDF`。

```bash
pip install pymupdf

# 逐页讲解模板
python skill/root-m7-courseware-notes/scripts/build_template.py \
  --input 课件.pdf \
  --out 课件_讲解模板.md \
  --depth deep

# 复习笔记模板
python skill/root-m7-courseware-notes/scripts/build_template.py \
  --input 课件.pdf \
  --out 课件_笔记模板.md \
  --kind note
```

PPT/PPTX 先另存为 PDF；也可以把每页导出成 `page_1.png`、`page_2.png`… 放在一个目录，用 `--images 页面目录` 生成。

可选参数：

- `--depth brief|standard|deep|max`：每页篇幅起点 260 / 620 / 900 / 1400 字，默认 `deep`。
- `--glossary-file 术语表.txt`：把课程专用译名和符号锁进模板。
- `--title`：覆盖默认的课件标题。

模板生成后，让 Agent 按模板逐页补全。写完后跑：

```bash
python skill/root-m7-courseware-notes/scripts/qa_check.py 成品.md
# 安全自动修复「### 前后空行」「页首复述上页」两类问题
python skill/root-m7-courseware-notes/scripts/qa_check.py --fix 成品.md
```

`qa_check.py` 只查格式和跨页一致性：公式定界符/环境配对、页码连续、小标题空行、编号揉段、页首复述、正/花体 Z 的表述。它查不了数值真伪和推导对错，那部分仍要对着原课件抽查。

## 规范来源

规范来自根号M7手动版的模板与提示词，包含：

- 小标题分层与按版面顺序讲解；
- 公式、字母、上下标、单位、适用条件零删减；
- 符号首次出现给中文名和读法；
- 连续推导/例题只在块首页定位一次；
- 图表必须接本页文字或公式；
- 去 AI 味的 26 条模式；
- 交稿前自检、`VERIFY-REPORT`、整篇定名、程序化质检。

`references/handoff-prompts.md` 保留了手动模式的全套提示词；如果要把模板交给网页版模型，仍然可以按原来的方式复制粘贴。

## 上传到 GitHub

在仓库根目录执行（把 `<your-name>` 换成你的 GitHub 用户名）：

```bash
git init
git add .
git commit -m "feat: 根号M7 课件讲解 Skill"
git branch -M main
git remote add origin https://github.com/<your-name>/root-m7-courseware-notes.git
git push -u origin main
```

发布前建议补一个 `LICENSE`。如果要让别人自由复用，MIT 或 CC BY 4.0 都比较合适；如果只想保留署名、不允许商用，选 CC BY-NC 4.0。仓库本身没有默认附加许可证。
