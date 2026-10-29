// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 theme.uts。

/** 阅读页主题（正文/标题/浮层/抽屉成组切换） */
export type ReaderTheme = {
	/** 页面/正文区背景 */
	readerBg: string
	/** 正文文字色 */
	bodyColor: string
	/** 标题文字色 */
	titleColor: string
	/** 章节标签色 */
	labelColor: string
	/** 弱化文字色 */
	mutedColor: string
	/** 目录章节文字色 */
	chapterTextColor: string
	/** 顶部菜单毛玻璃背景 */
	menuTopBg: string
	/** 底部面板毛玻璃背景 */
	menuBottomBg: string
	/** 浮层描边色 */
	menuBorderColor: string
	/** 当前章节高亮（正向蓝） */
	activeBlue: string
	/** 书签下拉/移除遮罩背景（夜间用浅色与暗底区分） */
	maskBg: string
	/** 遮罩内提示文字色（随遮罩明暗切换） */
	maskTextColor: string
	/** 划词气泡背景（夜间提亮与暗底区分） */
	popoverBg: string
	/** 底部控制栏投影（夜间切换为白色微光） */
	panelShadow: string
	/** 设置面板控件背景（夜间灰底，日间白底） */
	controlBg: string
	/** 设置面板控件描边 */
	controlBorder: string
	/** 设置面板控件文字色（夜间白字突出） */
	controlText: string
	/** 翻页覆盖模式遮罩面色（浅色纸面用墨色加深，暗色纸面用浅白提亮） */
	coverMaskBg: string
	/** 想法查看面板底色（日间纯白与页面背景区分，夜间随浮层底色） */
	thoughtPanelBg: string
}
