# 课件讲解与复习笔记 Skill

把 PPT / PDF 课件写成逐页中文讲解稿，或写成可以直接抄的复习笔记。

Skill 标识：`courseware-lecture-notes`

这是一套从实际课件讲解中提炼出来的 Agent Skill：由当前 Agent 自己读取课件、逐页写作，再用脚本做确定性质检。它把“怎么认小标题、怎么按版面顺序讲、公式和条件怎么保留、复习笔记怎么写得能直接抄”整理成了可重复执行的流程。

## 它解决什么

- 逐页讲解：先认小标题，再按版面顺序讲；公式、符号、上下标、条件零删减；补推导、讲物理意义、标易错点。
- 复习笔记：只留定义、结论、适用条件、步骤、对比和易错点，不写导入、过渡和解题表演。
- 交稿质量：强制写 `VERIFY-REPORT`，跑程序化质检，整篇定名，保留页码和 `## Pn` 骨架。
- 可复现：规范、提示词、模板生成和质检都在仓库里，不依赖某一次对话的上下文。

## 适合谁

- 有 PDF / PPT 课件，想直接得到逐页讲解稿，而不是零散摘要。
- 需要把英文课件讲成中文，同时保留公式、符号和适用条件。
- 考前想要一份能直接抄进笔记本的复习笔记。
- 想把这套讲解流程交给支持 Agent Skills 的客户端复用。

## 仓库结构

```text
root-m7-courseware-notes/
├── README.md
└── skill/
    └── courseware-lecture-notes/
        ├── SKILL.md
        ├── references/
        │   ├── lecture-spec.md       # 逐页讲解完整规范
        │   ├── notes-spec.md          # 复习笔记完整规范
        │   └── handoff-prompts.md     # 可复制给其他模型的提示词
        └── scripts/
            ├── build_template.py      # PDF/页面图片 → 讲解/笔记模板
            ├── headings.py            # 小标题线索识别
            └── qa_check.py            # 零 token 程序化质检
```

## 安装

把 `skill/courseware-lecture-notes` 整个文件夹复制到你使用的 Agent 的 skills 目录。不同客户端的目录不同；只要该客户端支持 Agent Skills，放入其 skills 根目录即可。

安装后不需要背很长的提示词，直接说：

```text
用课件讲解规范，把这份 PDF 写成逐页讲解。
```

或：

```text
用复习笔记规范，把这份课件写成能直接抄的笔记。
```

Agent 会读取 `SKILL.md`，按里面的工作流选择规范、生成模板、逐页写作、跑质检。

## 命令行用法（不经过 Agent 也可以先建模板）

需要 Python 3.10+；PDF 渲染依赖 `PyMuPDF`。

```bash
pip install pymupdf

# 逐页讲解模板
python skill/courseware-lecture-notes/scripts/build_template.py \
  --input 课件.pdf \
  --out 课件_讲解模板.md \
  --depth deep

# 复习笔记模板
python skill/courseware-lecture-notes/scripts/build_template.py \
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
python skill/courseware-lecture-notes/scripts/qa_check.py 成品.md
# 安全自动修复「### 前后空行」「页首复述上页」两类问题
python skill/courseware-lecture-notes/scripts/qa_check.py --fix 成品.md
```

`qa_check.py` 只查格式和跨页一致性：公式定界符/环境配对、页码连续、小标题空行、编号揉段、页首复述、正/花体 Z 的表述。它查不了数值真伪和推导对错，那部分仍要对着原课件抽查。

## 规范里有什么

- 小标题分层与按版面顺序讲解；
- 公式、字母、上下标、单位、适用条件零删减；
- 符号首次出现给中文名和读法；
- 连续推导/例题只在块首页定位一次；
- 图表必须接本页文字或公式；
- 去 AI 味的 26 条模式；
- 交稿前自检、`VERIFY-REPORT`、整篇定名、程序化质检。

`references/handoff-prompts.md` 保留了可复制给其他模型的提示词；如果要把模板交给网页版模型或其他 Agent，可以按原来的方式复制粘贴。

## 许可证

发布前建议补一个 `LICENSE`。如果要让别人自由复用，MIT 或 CC BY 4.0 都比较合适；如果只想保留署名、不允许商用，选 CC BY-NC 4.0。仓库本身没有默认附加许可证。
