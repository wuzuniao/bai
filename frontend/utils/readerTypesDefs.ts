// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 readerTypes.uts。

/** 目录章节（目录列表与正文页头共用） */
export type Chapter = {
	id: number
	/** 目录标题（如：第1章 章节名） */
	title: string
	/** 正文页章节标签（如：第 1 章） */
	label: string
	/** 正文页大标题 */
	contentTitle: string
	/** 当前阅读章节高亮（由阅读页 currentChapterId 驱动） */
	active: boolean
}

/** 书签（正文下滑切换添加/移除） */
export type Bookmark = {
	chapterId: number
	/** 章内页码（0-based） */
	pageIndex: number
}

/** 章节段落（正文渲染/分页/划线定位共用；text 为段落文本，段落索引是划线/想法/进度的定位键） */
export type Paragraph = {
	text: string
}

/** 想法/划线卡片（目录抽屉卡片列表项） */
export type NoteRecord = {
	cid: number
	origin: number
	qStart: number
	quote: string
	content: string
}

/** 正文字体选项（设置面板字体列表） */
export type FontOption = {
	key: string
	label: string
	/** CSS 字体栈：缺失字体自动回退到后续项，末位 sans-serif 即系统黑体 */
	family: string
}

/** 划线记录：按「章+段落」记录（跨章划线的段索引属于各自章） */
export type UnderlineEntry = {
	/** 划线发生所在章 */
	cid: number
	origin: number
	/** 段内字符索引闭区间 [start, end] 列表 */
	ranges: number[][]
}

/** 想法记录：关联到选区区间（跨段跨章） */
export type Thought = {
	fromCid : number
	fromOrigin : number
	fromStart : number
	toCid : number
	toOrigin : number
	toEnd : number
	/** 保存时的划线文本快照 */
	quote: string
	content: string
}

/** 选区覆盖段序列项（页面 spanSegs 展开结果，划线按项写入所在章） */
export type SpanSeg = {
	cid : number
	origin : number
	start : number
	end : number
}

/** 划词选区（跨段跨章）：从起点段/字符到终点段/字符的闭区间，手柄拖动可跨段落选择 */
export type SelSpan = {
	fromCid : number
	fromOrigin : number
	fromStart : number
	toCid : number
	toOrigin : number
	toEnd : number
}

/** 分享卡片内容快照（点分享时由页面按选区计算，组件渲染与绘制共用） */
export type ShareQuoteCtx = {
	/** 引文前上/下文（两档透明度渐出） */
	farBefore: string
	nearBefore: string
	/** 选中文本 */
	quote: string
	/** 引文后上/下文（两档透明度渐出） */
	nearAfter: string
	farAfter: string
	/** 选区关联想法内容（空=纯划线分享） */
	thoughtText: string
	/** 出处（选区终点章标题） */
	source: string
	/** 书名 */
	bookTitle: string
}

/** 阅读设置（字号/翻页模式/主题/字体，真源本地存储：ReaderControl 组件读写，页面应用渲染） */
export type ReaderSettings = {
	fontSize: number
	pageTurn: string
	theme: string
	fontKey: string
}

/** 排版度量（正文分页/划词换算共用的行参数） */
export type TextMetrics = {
	/** 每行字数 */
	perLine: number
	/** 行高（px） */
	lineH: number
	/** 自然字距（=字号；0.4rpx 字距在原生渲染实测未生效，按 APP 端实测每行字数校准） */
	charW: number
	/** 满行实际字距（正文两端对齐拉伸后按行宽均分） */
	fullCharW: number
	/** 段落首行缩进（px，= 字号×2；首行字符容量为 perLine-2，行列换算与分页容量共用此值） */
	indentPx: number
}

/** 拖动中的段落视口矩形缓存项（触点→段落映射，支撑跨段拖动；len 为本 rect 文本切片长度供字符换算，from 为切片在整段中的起始偏移） */
export type ParaRect = {
	cid : number
	origin : number
	left : number
	top : number
	bottom : number
	len : number
	/** 本 rect 文本切片在整段中的起始字符（流式分页段落跨页时非 0；换算原段坐标需加此偏移） */
	from : number
	/** 合并行前段字符数（首页诗宽屏"每行一句"：一个渲染行并置两个笔记段；-1=无合并即单段行；UTS 类型声明不支持属性默认值，构造处须显式传值） */
	firstLen : number
	/** 合并行后段所属段 origin（宽屏合并行=前段 origin+1；-1=无合并） */
	secondOrigin : number
}
