// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 books.uts。

/** 书架书籍（书架页展示与排序的唯一数据源；云端字段 + 本机 path 合并结果） */
export type LocalBook = {
	/** 云端书籍 id（导入登记时由后端分配） */
	id: number
	/** 书名（导入时取文件名去扩展名） */
	title: string
	/** 作者署名（本地导入无作者信息，恒为空串；封面深灰卡布局位） */
	author: string
	/** 导入文件格式大写水印（TXT/PDF），封面角落展示 */
	format: string
	/** 正文文件在沙盒中的路径（'' 表示本设备无正文，需重新导入同名文件） */
	path: string
	/** 文件字节数 */
	size: number
	/** 导入时间戳（ms） */
	addedAt: number
	/** 最近阅读时间戳（ms，0=未读） */
	lastReadAt: number
	/** 上次阅读到的章节 id（-1=未读；PDF 书恒为 -1，进度用 lastPercent） */
	lastChapter: number
	/** 章内页码 0-based（txt 恢复定位） */
	lastPageIndex: number
	/** 滚动模式滚动位置 px（txt 恢复定位） */
	lastScrollTop: number
	/** 最近阅读百分比（0-100，仅 PDF 书使用；txt 书恒为 0） */
	lastPercent: number
	/** PDF 首页高/宽比（页面 wrapper 等比布局依据；txt 书为 0） */
	pdfRatio: number
	/** 章节总数（txt=解析章节数，含序章；PDF=页数） */
	chapterCount: number
	/** 第一章前有前置内容并生成序章（导入时固化） */
	hasPreface: boolean
	/** 离线改动待回补（未登录复用云端行导入/阅读后置位；登录回补成功清除） */
	dirty: boolean
}

/** 阅读进度（txt：章节/页码/滚动位置） */
export type BookProgress = {
	chapterId: number
	/** 章内页码（0-based） */
	pageIndex: number
	/** 滚动模式的滚动位置（px） */
	scrollTop: number
}

/** PDF 阅读进度（滚动位置百分比 + 首页宽高比，用于布局与恢复定位） */
export type PdfProgress = {
	percent: number
	/** 首页高/宽比（页面 wrapper 等比布局依据） */
	ratio: number
}

/** 阅读会话时钟（onShow 起算、根节点 touchstart 续期、onHide/onUnload 结算；reader 与 pdfreader 共用同一结算口径） */
export type ReadingClock = {
	/** 页面显示：起算本次阅读 */
	onShown : () => void
	/** 根节点触摸：记录操作时间；距上次操作超时则上一会话以「最后操作+10min」入账并重新起算（虚拟书 0 不计时） */
	onActive : (bookId : number) => void
	/** 结算本次阅读：会话入账（<1 分钟内部丢弃），结束点截断至「最后操作+10min」（页面后台停留期间不计时长）；
	 *  调用方自行守卫虚拟书 0 与进度回写 */
	settle : (bookId : number) => void
}
