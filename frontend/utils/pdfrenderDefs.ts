// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 pdfrender.uts。

export type PdfPageDim = {
	/** 页宽（PDF point 单位） */
	w: number
	/** 页高（PDF point 单位） */
	h: number
}

/** 已打开的 PDF 会话（阅读页持有，逐页渲染完成后必须 close 释放文件句柄） */
export type PdfSession = {
	/** 总页数 */
	pageCount: number
	/** 渲染指定页（0-based）为 JPEG 写入 outPath，targetWidth 为目标像素宽（高度按页比例等比） */
	renderPage : (index : number, outPath : string, targetWidth : number) => Promise<void>
	/** 取指定页宽高（point 单位，用于布局等比计算） */
	pageSize : (index : number) => Promise<PdfPageDim>
	/** 关闭会话释放文件句柄 */
	close : () => void
}
