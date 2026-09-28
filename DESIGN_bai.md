---
version: alpha
name: wuzuniao-design-analysis
description: 一套面向古诗词、小说等文学阅读项目的设计系统——以异常厚重的近黑显示无衬线字体（字重 900，64–126 px）与纯粹的墨黑品牌强调色 (#0E0F0C)、白色的中性表层，以及铺在雾灰白画布 (#F4F4F2) 上的圆角白色卡片为核心；诗词卡片内的诗句正文以思源宋体（Source Han Serif）呈现古典纸感（次要兼容通用宋体），诗词标题、作者元信息与卡片之外的界面文字一律保持思源黑体——现代极简的界面骨架之下，包裹一页专属于古典文学的纸面。

colors:
  primary: "#0e0f0c"
  on-primary: "#ffffff"
  primary-active: "#2e2e2b"
  primary-neutral: "#a3a3a0"
  primary-pale: "#e9e9e6"
  ink: "#0e0f0c"
  ink-deep: "#2b2b28"
  body: "#454745"
  mute: "#868685"
  canvas: "#ffffff"
  canvas-soft: "#f4f4f2"
  positive: "#1e40af"
  positive-deep: "#1e3a8a"
  warning: "#ffd11a"
  warning-deep: "#b86700"
  warning-content: "#4a3b1c"
  negative: "#d03238"
  negative-deep: "#a72027"
  negative-darkest: "#a7000d"
  negative-bg: "#320707"
  accent-orange: "#ffc091"

typography:
  display-mega:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, -apple-system, sans-serif
    fontSize: 126px
    fontWeight: 900
    lineHeight: 107.1px
  display-xxl:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 96px
    fontWeight: 900
    lineHeight: 81.6px
  display-xl:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 64px
    fontWeight: 900
    lineHeight: 54.4px
  display-lg:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 47px
    fontWeight: 400
    lineHeight: 70.5px
    letterSpacing: -0.108px
  display-md:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 40px
    fontWeight: 900
    lineHeight: 34px
  display-sm:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 32px
    fontWeight: 600
    lineHeight: 38.4px
    letterSpacing: -0.96px
  display-xs:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 24px
    fontWeight: 600
    lineHeight: 31.2px
    letterSpacing: -0.48px
  body-lg:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 20px
    fontWeight: 400
    lineHeight: 30px
  body-md:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
  body-md-strong:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 16px
    fontWeight: 600
    lineHeight: 24px
  body-sm:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
  body-sm-strong:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 14px
    fontWeight: 600
    lineHeight: 20px
  caption:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  button-md:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 16px
    fontWeight: 600
    lineHeight: 24px
  poem-title:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 28px
    fontWeight: 600
    lineHeight: 44.8px
    letterSpacing: 1px
  poem-body:
    fontFamily: "Source Han Serif SC", "Noto Serif SC", "思源宋体", "Songti SC", "STSong", "SimSun", serif
    fontSize: 22px
    fontWeight: 400
    lineHeight: 44px
    letterSpacing: 1.5px
  poem-meta:
    fontFamily: "Source Han Sans SC", "Noto Sans SC", "思源黑体", Inter, system-ui, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 24px

rounded:
  none: 0px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  pill: 9999px
  full: 9999px

spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  2xl: 32px
  3xl: 48px

components:
  nav-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm-strong}"
    padding: "{spacing.md} {spacing.xl}"
  nav-link:
    textColor: "{colors.ink}"
    typography: "{typography.body-sm-strong}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.md} {spacing.xl}"
  button-secondary:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.md} {spacing.xl}"
  button-tertiary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.md} {spacing.xl}"
  button-icon-circular:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    padding: "{spacing.sm}"
  text-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.md} {spacing.lg}"
  card-content:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  card-feature-mist:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  card-feature-silver:
    backgroundColor: "{colors.primary-pale}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  card-feature-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  hero-band:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.display-mega}"
    padding: "{spacing.3xl} {spacing.xl}"
  hero-band-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.display-mega}"
    padding: "{spacing.3xl} {spacing.xl}"
  content-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-md}"
    padding: "{spacing.3xl} {spacing.xl}"
  item-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.canvas-soft}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  poem-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    titleTypography: "{typography.poem-title}"
    bodyTypography: "{typography.poem-body}"
    metaTypography: "{typography.poem-meta}"
    metaColor: "{colors.body}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  badge-positive:
    backgroundColor: "{colors.positive-deep}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm-strong}"
    rounded: "{rounded.pill}"
    padding: "{spacing.xs} {spacing.md}"
  badge-negative:
    backgroundColor: "{colors.negative-bg}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm-strong}"
    rounded: "{rounded.pill}"
    padding: "{spacing.xs} {spacing.md}"
  footer:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas-soft}"
    typography: "{typography.body-sm}"
    padding: "{spacing.3xl} {spacing.xl}"

  # ─── Examples (illustrative) — auto-derived; resolve any TO_FILL markers below ───
  ex-pricing-tier:
    description: "Default Pricing tier card. Re-uses feature-card chrome with brand canvas-soft surface."
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    borderColor: "{colors.mute}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  ex-pricing-tier-featured:
    description: "Featured/highlighted tier — polarity-flipped surface (dark fill + light text in light mode, light fill + dark text in dark mode)."
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  ex-product-selector:
    description: "What's Included summary card — re-purposed for SaaS / B2B verticals (NOT a literal product gallery)."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  ex-cart-drawer:
    description: "Subscription summary — re-purposed for SaaS / B2B (line items per add-on, not literal cart)."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
    item-divider: "{colors.canvas-soft}"
  ex-app-shell-row:
    description: "Sidebar nav row inside the App Shell example. Active state uses brand primary as the indicator."
    backgroundColor: "{colors.canvas}"
    activeIndicator: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md} {spacing.lg}"
  ex-data-table-cell:
    description: "Default data-table th + td chrome. Header uses mono-caps eyebrow typography; body uses body-sm."
    headerBackground: "{colors.canvas-soft}"
    headerTypography: "{typography.caption}"
    bodyTypography: "{typography.body-sm}"
    cellPadding: "{spacing.md} {spacing.lg}"
    rowBorder: "{colors.canvas-soft}"
  ex-auth-form-card:
    description: "Sign-in / sign-up card. Re-uses feature-card chrome with text-input primitives inside."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  ex-modal-card:
    description: "Modal dialog surface — same chrome as feature-card with elevated shadow."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  ex-empty-state-card:
    description: "Empty-state illustration frame."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.xl}"
    padding: "{spacing.3xl}"
    captionTypography: "{typography.body-md}"
  ex-toast:
    description: "Toast notification surface — feature-card shape + medium shadow."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.xl}"
    padding: "{spacing.md} {spacing.lg}"
    typography: "{typography.body-sm}"

---


## 概览

无足鸟 —— 一套为古诗词、小说等文学阅读项目打造的设计系统 —— 以一组标志性的搭配确立自身语言：纯粹的墨黑 `{colors.primary}`（`#0e0f0c`）被用作 CTA 胶囊按钮与品牌强调色，衬在一整条贯穿首屏的雾灰白画布 `{colors.canvas-soft}`（`#f4f4f2`）之上，再配上与之同源的近黑墨色 `{colors.ink}`（`#0e0f0c`）—— 系统只有一个黑：按钮、标题、正文与页脚共享同一份墨色，白色画布则是它唯一的舞台。整个系统在克制的极简框架之下专注于一件事 —— 阅读：大量留白、硕大的圆角卡片，一副字重高达 900、撑起每个首屏大标题的异常厚重显示字体，以及一张诗句正文以思源宋体呈现、标题与元信息以思源黑体标注的诗词卡片。

显示字体是品牌第二个决定性的声音。**思源黑体**字体族在最大首屏上以 900 字重、64 px 到 126 px 的尺度承载首屏显示。品牌将思源黑体 900 与字重 600 的 **Inter** 搭配用于次级显示 —— 这种厚实、自带专属气质的字体面与 Inter 的中性之间形成的对比，构建出独特的层级：思源黑体 900 用于品牌高光时刻，Inter 600 用于其余一切。

**思源宋体**是系统唯一的衬线之声，且只出现在诗词卡片内部。诗句正文一律以思源宋体渲染（次要兼容通用宋体），以衬线的笔触还原纸上阅读的古典质感；而诗词卡片内的标题与作者元信息，连同卡片之外的导航、按钮、表单与说明文字，全部保持思源黑体 —— 宋体只属于诗句正文，黑体属于其余一切。

卡片普遍采用胶囊圆角 —— `{rounded.xl}` 24 px 是品牌标志性的卡片圆角。按钮采用同样的 24 px 胶囊矩形造型。品牌绝不在 UI 元素上使用尖角；这种视觉上的柔和感正是其友好调性的一部分。

**核心特征：**
- 唯一的墨黑 CTA 强调色 `{colors.primary}`（`#0e0f0c`）—— 品牌通用的主操作色。没有第二种强调色，系统只有一个黑。
- 双层显示字体 —— 思源黑体（字重 900，首屏尺度）+ Inter（字重 600，次级显示尺度）。这种对比正是品牌的字体叙事。
- 诗词卡片 `{components.poem-card}` —— 诗句正文的唯一衬线舞台：卡片内的诗句以思源宋体呈现（次要兼容通用宋体），诗词标题、作者元信息与卡片外的一切文字保持思源黑体。
- `{rounded.xl}` 24 px 是品牌规范的卡片与按钮圆角。宽厚、友好。
- 白色调表层：纯白 `{colors.canvas}`（`#ffffff`）与雾灰白 `{colors.canvas-soft}`（`#f4f4f2`）共同构成品牌的底色基调 —— 白色承载内容，雾灰白专用于柔和的次级表层与卡片呼吸。
- 一套完整的语义化色板：正向深蓝族、警示黄族、负向红族 —— 每一种都记录了内容 / 悬停 / 激活变体，供产品内使用。黑白只承载结构，状态语义交给色相。

## 颜色

### 品牌与强调色
- **墨黑**（`{colors.primary}` — `#0e0f0c`）：品牌通用的 CTA 颜色。每一个主按钮、每一个通用胶囊型操作、品牌的标志强调色。与文本墨色同源 —— 系统只有一个黑。
- **墨黑激活态**（`{colors.primary-active}` — `#2e2e2b`）：用于激活 / 悬停态的深炭灰。
- **中性灰**（`{colors.primary-neutral}` — `#a3a3a0`）：中饱和度的灰，用作中性激活填充。
- **浅灰**（`{colors.primary-pale}` — `#e9e9e6`）：最浅的灰，用于柔和的表层色调 / 徽章背景。

### 表层
- **画布**（`{colors.canvas}` — `#ffffff`）：卡片内部与内容带的纯白色。
- **柔和画布**（`{colors.canvas-soft}` — `#f4f4f2`）：雾灰白的页面背景。奠定品牌的白色基调。

### 文本
- **墨色**（`{colors.ink}` — `#0e0f0c`）：纯黑系的近黑 —— 品牌默认文本与标题颜色。
- **深墨色**（`{colors.ink-deep}` — `#2b2b28`）：深炭灰，用作深色强调文本 / 深色表层文字色。
- **正文色**（`{colors.body}` — `#454745`）：次级正文文本。
- **弱文本色**（`{colors.mute}` — `#868685`）：最低优先级的文本 —— 说明文字、占位符、细则。

### 语义色
- **正向**（`{colors.positive}` — `#1e40af`）：成功指示色（深蓝）。在黑白主调中承担唯一的正向色相 —— 黑色承载交互，蓝色承载确认。
- **正向深**（`{colors.positive-deep}` — `#1e3a8a`）：按下的正向状态 / 正向徽章背景。
- **警示**（`{colors.warning}` — `#ffd11a`）：提醒指示色。
- **警示深**（`{colors.warning-deep}` — `#b86700`）：按下的警示状态。
- **警示内容色**（`{colors.warning-content}` — `#4a3b1c`）：警示表层上的文本色。
- **负向**（`{colors.negative}` — `#d03238`）：破坏 / 错误红。
- **负向深**（`{colors.negative-deep}` — `#a72027`）：按下的破坏状态。
- **负向最深**（`{colors.negative-darkest}` — `#a7000d`）：最高强调程度的破坏文本。
- **负向背景**（`{colors.negative-bg}` — `#320707`）：用于破坏型提示框背景的深栗色。

### 品牌强调色 —— 第三层级
- **强调橙**（`{colors.accent-orange}` — `#ffc091`）：唯一的第三层强调色，用于插画内容 / 定价卡片内的明亮桃色，与黑白主调形成冷暖对比。

## 字体排印

### 字体族
三套字体面阶梯式支撑整个系统：
1. **思源黑体（Source Han Sans SC / Noto Sans SC）** —— 专属几何无衬线字体，以异常厚重的 900 字重用于所有首屏显示，并承载诗词卡片之外的全部界面文字。该字体面是品牌的排印标志。始终使用 900 字重，在营销表层上绝不变轻。
2. **Inter** —— 用于次级显示（字重 600）、界面正文以及表单标签。加载时启用 `font-feature-settings: "calt"` 以获得上下文替代字形。
3. **思源宋体（Source Han Serif SC / Noto Serif SC）** —— 系统唯一的衬线字体，专用于诗词卡片内的诗句正文。次要兼容通用宋体（Songti SC / STSong / SimSun）。宋体绝不越出诗句正文的边界；诗词卡片内的诗词标题与作者 / 朝代元信息使用思源黑体。

### 层级

| 令牌 | 字号 | 字重 | 行高 | 字间距 | 用途 |
|---|---|---|---|---|---|
| `{typography.display-mega}` | 126px | 900 | 107.1px | 0 | 最大尺度的首屏模板字。 |
| `{typography.display-xxl}` | 96px | 900 | 81.6px | 0 | 次级首屏尺度。 |
| `{typography.display-xl}` | 64px | 900 | 54.4px | 0 | 标准首屏大标题。 |
| `{typography.display-lg}` | 47px | 400 | 70.5px | -0.108px | 较轻的次级显示。 |
| `{typography.display-md}` | 40px | 900 | 34px | 0 | 区块 / 卡片标题。 |
| `{typography.display-sm}` | 32px | 600 | 38.4px | -0.96px | Inter 渲染的区块标题。 |
| `{typography.display-xs}` | 24px | 600 | 31.2px | -0.48px | 子区块显示。 |
| `{typography.body-lg}` | 20px | 400 | 30px | 0 | 引导段落。 |
| `{typography.body-md}` | 16px | 400 | 24px | 0 | 默认正文。 |
| `{typography.body-md-strong}` | 16px | 600 | 24px | 0 | 加粗行内正文。 |
| `{typography.body-sm}` | 14px | 400 | 20px | 0 | 次级正文。 |
| `{typography.body-sm-strong}` | 14px | 600 | 20px | 0 | 加粗说明 / 导航链接。 |
| `{typography.caption}` | 12px | 400 | 16px | 0 | 细则。 |
| `{typography.button-md}` | 16px | 600 | 24px | 0 | 按钮标签。 |
| `{typography.poem-title}` | 28px | 600 | 44.8px | 1px | 诗词卡片标题（思源黑体）。 |
| `{typography.poem-body}` | 22px | 400 | 44px | 1.5px | 诗词卡片诗句正文（思源宋体）。 |
| `{typography.poem-meta}` | 14px | 400 | 24px | 0 | 诗词卡片作者 / 朝代元信息（思源黑体）。 |

### 原则
- **首屏用 900 字重，其余一切用 600 字重。** 品牌的显示上限是全黑字重；其下皆为半粗体。
- **思源黑体承载界面之声（含诗词标题与元信息），Inter 负责实用文本，思源宋体只属于诗词卡片内的诗句正文。** 严格的角色分工 —— 诗句是宋体的纸面，其余一切是黑体的界面。

### 关于字体替代的说明
思源黑体为 Adobe 与 Google 联合发布的开源字体（亦以 Noto Sans SC 之名分发）。开源替代方案：
- **显示字（首屏）** —— *思源黑体 / Noto Sans SC* 字重 900，或 *Inter* 字重 900、*Manrope* 字重 800 / 900，均可捕捉几何厚重感。*Geist* 字重 800 是尚可的第二选择。
- **次级显示 + 正文** —— *Inter* 是品牌实际的第二字体面。
- **诗句正文（诗词卡片内）** —— *思源宋体 / Noto Serif SC*（Adobe 与 Google 联合发布的开源衬线字体）为首选；次要兼容通用宋体：*Songti SC*（macOS）、*STSong*、*SimSun*（Windows 中易宋体），最终以 serif 兜底。诗词标题与元信息无需衬线替代 —— 随全局思源黑体。

## 布局

### 间距系统
- **基础单位**：4 px。
- **令牌**：`{spacing.xxs}` 2 px · `{spacing.xs}` 4 px · `{spacing.sm}` 8 px · `{spacing.md}` 12 px · `{spacing.lg}` 16 px · `{spacing.xl}` 24 px · `{spacing.2xl}` 32 px · `{spacing.3xl}` 48 px。
- **区块内边距**：桌面端各 band 上下使用 `{spacing.3xl}` 48 px。
- **卡片内部**：卡片使用 `{spacing.xl}` 24 px。

### 栅格与容器
- 首屏：桌面端为分栏布局（左侧大标题，右侧交互卡片）；移动端堆叠。
- 特性栅格：桌面端 2 列 / 3 列。

### 响应式策略

#### 断点

| 名称 | 宽度 | 关键变化 |
|---|---|---|
| 移动端 | < 768px | 首屏堆叠；交互卡片在大标题下方占满整行；栅格 1 列。 |
| 平板 | 768–1023px | 栅格 2 列。 |
| 桌面端 | ≥ 1024px | 首屏分栏；完整栅格。 |

#### 触控目标
按钮高度约 48 px（12 px 垂直内边距 + 24 px 行高）。全宽度均满足 WCAG AAA。

#### 图像行为
摄影素材稀疏；品牌偏好卡片内的插画 SVG 与产品模型图。

## 层级与深度

| 层级 | 处理方式 | 用途 |
|---|---|---|
| 层级 0 —— 扁平 | 无阴影，无边框。 | 默认。 |
| 层级 1 —— 深色细线 | 1 px 实线 `{colors.ink}` 边框。 | 第三层级描边按钮、表单输入。 |
| 层级 2 —— 柔和卡片 | 隐含的层级 0 白色卡片置于雾灰白画布之上 —— 表层对比即是高度。 | 雾灰白首屏带上的卡片。 |

品牌以表层对比（`{colors.canvas-soft}` 背景 vs `{colors.canvas}` 卡片）作为主要的高度提示。

## 形状

### 圆角尺度

| 令牌 | 数值 | 用途 |
|---|---|---|
| `{rounded.none}` | 0px | 满幅 band。 |
| `{rounded.sm}` | 8px | 行内胶囊、小徽章。 |
| `{rounded.md}` | 12px | 表单输入、较小构件。 |
| `{rounded.lg}` | 16px | 中等尺寸卡片。 |
| `{rounded.xl}` | 24px | 品牌规范的按钮 + 卡片圆角。 |
| `{rounded.pill}` | 9999px | 状态胶囊与全圆角强调。 |
| `{rounded.full}` | 9999px | 圆形图标容器。 |

## 组件

### 按钮

**`button-primary`** —— 墨黑 CTA 胶囊按钮。
- 背景 `{colors.primary}`，文本 `{colors.on-primary}`，标签 `{typography.button-md}`，内边距 `{spacing.md} {spacing.xl}`，形状 `{rounded.xl}` 24 px。

**`button-secondary`** —— 雾灰白的次级按钮。
- 背景 `{colors.canvas-soft}`，文本 `{colors.ink}`，相同的字体 / 内边距 / 形状。

**`button-tertiary`** —— 白色描边的第三层级按钮。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，1 px 实线 `{colors.ink}` 边框，相同的字体 / 内边距 / 形状。

**`button-icon-circular`** —— 圆形图标按钮。
- 背景 `{colors.canvas}`，墨色图标，形状 `{rounded.full}`。

### 卡片与容器

**`card-content`** —— 默认的白色卡片。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，内边距 `{spacing.xl}`，形状 `{rounded.xl}`。无边框，置于雾灰画布之上。

**`card-feature-mist`** —— 雾灰白的特性卡片。
- 背景 `{colors.canvas-soft}`，文本 `{colors.ink}`，内边距 `{spacing.xl}`，形状 `{rounded.xl}`。

**`card-feature-silver`** —— 银灰特性卡片。
- 背景 `{colors.primary-pale}`，文本 `{colors.ink}`，内边距 `{spacing.xl}`，形状 `{rounded.xl}`。

**`card-feature-dark`** —— 极性翻转的暗色卡片，配白色文本。
- 背景 `{colors.ink}`，文本 `{colors.canvas}`（纯白！），内边距 `{spacing.xl}`，形状 `{rounded.xl}`。用于推广时刻。

**`item-card`** —— 品牌的标志性内容卡片（通用，可承载任意条目信息）。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，1 px 实线 `{colors.canvas-soft}` 边框，内边距 `{spacing.xl}`，形状 `{rounded.xl}`。标题用 `{typography.body-md-strong}`，元数据用 `{colors.body}`。

**`poem-card`** —— 诗词卡片：诗句正文的专属载体（古诗词、诗句摘录、小说选段等阅读内容）。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，内边距 `{spacing.xl}`，形状 `{rounded.xl}`。**仅诗句正文使用思源宋体**（次要兼容通用宋体）：诗句用 `{typography.poem-body}`；诗词标题用 `{typography.poem-title}`、作者 / 朝代元信息用 `{typography.poem-meta}`（颜色 `{colors.body}`），均为思源黑体 —— 卡片内外，除诗句外的一切文字保持思源黑体。

### 输入与表单

**`text-input`** —— 规范文本输入框。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，1 px 实线 `{colors.ink}` 边框，正文用 `{typography.body-md}`，内边距 `{spacing.md} {spacing.lg}`，形状 `{rounded.md}`。

### 导航

**`nav-bar`** —— 吸顶顶部导航。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，内边距 `{spacing.md} {spacing.xl}`。

**`nav-link`** —— 导航内的链接项。
- 文本 `{colors.ink}`，使用 `{typography.body-sm-strong}`。

**`footer`** —— 暗色页脚带。
- 背景 `{colors.ink}`，文本 `{colors.canvas-soft}`，内边距 `{spacing.3xl} {spacing.xl}`。正文用 `{typography.body-sm}`。

### 标志性组件

**`hero-band`** —— 雾灰白画布首屏带。
- 背景 `{colors.canvas-soft}`，文本 `{colors.ink}`，内边距 `{spacing.3xl} {spacing.xl}`。大标题用 `{typography.display-mega}`（思源黑体字重 900）。

**`hero-band-dark`** —— 极性翻转的暗色首屏。
- 背景 `{colors.ink}`，文本 `{colors.canvas}`（近黑底上的纯白大标题！），相同的内边距 / 尺度。

**`content-band`** —— 紧随首屏的白色内容带。
- 背景 `{colors.canvas}`，文本 `{colors.ink}`，内边距 `{spacing.3xl} {spacing.xl}`。区块标题用 `{typography.display-md}`。

**`badge-positive`** —— 正向状态胶囊。
- 背景 `{colors.positive-deep}`（深蓝底），文本 `{colors.on-primary}`（白），正文用 `{typography.body-sm-strong}`，内边距 `{spacing.xs} {spacing.md}`，形状 `{rounded.pill}` —— 与负向徽章（深栗底白字）形成对称的深色徽章语言。

**`badge-negative`** —— 负向状态胶囊。
- 背景 `{colors.negative-bg}`，文本白色，正文用 `{typography.body-sm-strong}`，内边距 `{spacing.xs} {spacing.md}`，形状 `{rounded.pill}`。

### 示例（示意）

> 自动派生自工具包镜像演示表层（`scripts/derive-examples-block.mjs`）。每个 `ex-*` 条目都引用品牌原生基础变量，以便下游消费者（`/preview-design`、`/generate-kit`）对相同的 10 个表层保持一致换肤。`TO_FILL` 标记表示缺失的基础变量 —— 在 LLM 判断环节处理。

**`ex-pricing-tier`** —— 默认定价档位卡片。复用特性卡片外观，采用品牌柔和画布表层。
- 属性：`backgroundColor`、`textColor`、`borderColor`、`rounded`、`padding`

**`ex-pricing-tier-featured`** —— 精选 / 高亮档位 —— 极性翻转的表层（浅色模式下深色填充 + 浅色文本，深色模式下浅色填充 + 深色文本）。
- 属性：`backgroundColor`、`textColor`、`rounded`、`padding`

**`ex-product-selector`** —— “包含内容”摘要卡片 —— 重新用于 SaaS / B2B 垂直场景（并非字面的产品画廊）。
- 属性：`backgroundColor`、`rounded`、`padding`

**`ex-cart-drawer`** —— 订阅摘要 —— 重新用于 SaaS / B2B（每项附加功能一行，并非字面的购物车）。
- 属性：`backgroundColor`、`rounded`、`padding`、`item-divider`

**`ex-app-shell-row`** —— 应用外壳示例中的侧边栏导航行。激活态以品牌主色作为指示符。
- 属性：`backgroundColor`、`activeIndicator`、`rounded`、`padding`

**`ex-data-table-cell`** —— 默认数据表 th + td 外观。表头使用等宽大写眉标字体；表体使用 body-sm。
- 属性：`headerBackground`、`headerTypography`、`bodyTypography`、`cellPadding`、`rowBorder`

**`ex-auth-form-card`** —— 登录 / 注册卡片。复用特性卡片外观，内部使用文本输入基础组件。
- 属性：`backgroundColor`、`rounded`、`padding`

**`ex-modal-card`** —— 模态对话框表层 —— 与特性卡片相同的外观，带提升阴影。
- 属性：`backgroundColor`、`rounded`、`padding`

**`ex-empty-state-card`** —— 空状态插图框。
- 属性：`backgroundColor`、`rounded`、`padding`、`captionTypography`

**`ex-toast`** —— 提示通知表层 —— 特性卡片造型 + 中等阴影。
- 属性：`backgroundColor`、`rounded`、`padding`、`typography`


## 注意事项

### 应该做
- 为每个主 CTA 保留 `{colors.primary}` 墨黑。黑色胶囊正是品牌的转化标志。
- 诗词卡片内仅诗句正文使用思源宋体（`{typography.poem-body}`），并保持宽松的行高与字间距 —— 那是系统里唯一的衬线舞台，为古典文学还原纸感；诗词标题（`{typography.poem-title}`）与作者 / 朝代元信息（`{typography.poem-meta}`）使用思源黑体。
- 首屏大标题使用 `{typography.display-mega}` / `{typography.display-xl}`，思源黑体字重 900。绝不可更轻。
- 按钮与卡片使用 `{rounded.xl}` 24 px。宽厚的圆角正是品牌的友好标志。
- 页面表层在 `{colors.canvas-soft}` 雾灰白画布 → `{colors.canvas}` 白色卡片之间循环切换。表层对比承载高度感。
- 产品内状态使用完整的语义色板（正向 / 警示 / 负向）—— 切勿将品牌黑复用作成功指示色；黑白只承载结构，状态语义交给深蓝 / 黄 / 红的色相。

### 不应该做
- 不要引入第二种品牌强调色。墨黑是唯一的身份色。
- 不要把宋体用在诗句正文之外 —— 诗词标题、作者元信息、导航、按钮、表单、页脚等文字一律思源黑体；衬线只属于卡片内的诗句正文。
- 不要以 700 或更轻的字重渲染首屏。品牌的显示字重是 900。
- 不要把 CTA 渲染成尖角矩形。24 px 胶囊几何形状不可妥协。
- 不要将墨黑 CTA 与深色表层搭配。品牌始终让黑色胶囊落在中性浅色表层上（雾灰白 / 纯白）。
- 不要为有效首屏字体排印用通用几何无衬线替代思源黑体 —— 这个专属字体面正是品牌之声。
