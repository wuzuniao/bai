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
	/** 右界（px）：逐字拖动的末字符右缘收敛用（首页诗行尾标点区窄于字格步进，避免手柄悬出文本） */
	right : number
	len : number
	/** 本 rect 文本切片在整段中的起始字符（流式分页段落跨页时非 0；换算原段坐标需加此偏移） */
	from : number
	/** 合并行前段字符数（首页诗宽屏"每行一句"：一个渲染行并置两个笔记段；-1=无合并即单段行；UTS 类型声明不支持属性默认值，构造处须显式传值） */
	firstLen : number
	/** 合并行后段所属段 origin（宽屏合并行=前段 origin+1；-1=无合并） */
	secondOrigin : number
	/** 段落逐字符左缘（px，段落坐标含缩进：charX[k]=第 k 字左界、charX[段长]=末字右界；
	 *  App 端 StaticLayout 逐字缓存下发、非 APP 端由离屏逐字探针实测下发（见 ParaGeom），
	 *  首页诗等无实测数据的端点为 null——null 时拖动退回均匀字格口径） */
	charX : number[] | null
	/** 段落逐行末字符下标（段落坐标，与 charX 配合做触点→字符逆映射）；null=无精确数据 */
	lineEnds : number[] | null
	/** 段落逐行真实右缘（px，段落坐标；行末字符的右界必须取它——charX[行末+1] 是下一行首字 x=0） */
	lineRights : number[] | null
}

/** 段落逐字几何（非 APP-ANDROID 端离屏逐字探针实测，字段口径与 App 端 StaticLayout 同构：
 *  真实换行 + 逐字左缘，供划词长按定位与手柄拖动做精确行列换算；均匀字格口径在标点禁则/半角字符下每行偏 1 字、段尾累计偏 3~4 字） */
export type ParaGeom = {
	/** 逐字左缘（px，段落坐标含首行缩进：charX[k]=段内第 k 字左界、charX[段长]=末字右界） */
	charX : number[]
	/** 逐行末字符下标（段内坐标，-1 表示该行只含缩进空格） */
	lineEnds : number[]
	/** 逐行真实右缘（px，段落坐标；行末字符右界不能取 charX[行末+1]） */
	lineRights : number[]
}

/** 逐字几何探针段落（非 APP-ANDROID 端屏外渲染项：单字符数组，逐字 text 的 v-for 源与实测矩形切分依据） */
export type CharProbePara = {
	chars : string[]
}

/** 段落想法/划线的行底线条带（App 端按 charX 逐行渲染；非 App 端线条由 text-decoration 着色，不产生带） */
export type ParaBand = {
	/** 内联定位样式（left/top/width/height，px；坐标系=所在段落视图） */
	style : string
	/** true=想法线条（正蓝）；false=划线线条（弱灰） */
	thought : boolean
}
