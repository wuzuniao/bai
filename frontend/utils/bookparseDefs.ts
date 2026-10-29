// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 bookparse.uts。

/** 解析章节（导入管线产物） */
export type ParsedChapter = {
	/** 目录标题（完整标题行） */
	title: string
	/** 正文页章节标签（如：第 12 章；无编号章为整行标题） */
	label: string
	/** 正文页大标题（编号后标题部分） */
	contentTitle: string
	/** 章内段落（非空行） */
	paragraphs: string[]
	/** 序章标记（第一章前的前置内容生成；打开时仅对导入时标记 hasPreface 的书保留，保证旧书章 id 与存量进度对齐） */
	preface: boolean
}

/** 同步结果统计 */
export type SyncResult = {
	/** 上传成功本数 */
	uploaded: number
	/** 下载成功本数 */
	downloaded: number
	/** 反向建档恢复本数（云端有对象而本地无书行） */
	restored: number
	/** 失败本数（单本失败不中断整体，继续同步其余） */
	failed: number
}
