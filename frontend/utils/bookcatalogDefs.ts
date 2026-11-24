// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 bookcatalog.uts。

/** 目录章节条目（from/to 为全文正文字符偏移区间 [from, to)，正文按章切片惰性读取） */
export type CatalogChapter = {
	/** 目录标题（完整标题行） */
	title: string
	/** 正文页章节标签（如：第 12 章；无编号章为整行标题） */
	label: string
	/** 正文页大标题（编号后标题部分） */
	contentTitle: string
	/** 序章标记（第一章前的前置内容生成） */
	preface: boolean
	/** 正文起始字符偏移（含） */
	from: number
	/** 正文结束字符偏移（不含） */
	to: number
}

/** 书籍目录（章节条目 + 全文正文） */
export type BookCatalog = {
	/** 正文文件字节数（与 LocalBook.size 比对做缓存校验） */
	size: number
	/** 章节条目（顺序即章 id 顺序） */
	chapters: CatalogChapter[]
	/** 全文正文字符串（正文惰性切片依据，不入缓存） */
	text: string
}
