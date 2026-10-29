// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 pagination.uts。

/** 页内渲染切片：段落在章内的索引 + 本页展示的字符闭区间 [from, to]（段落未被切断时 from=0、to=段长-1） */
export type PageSlice = {
	/** 段落在章内的索引（划线/想法/选区的定位键，坐标基于整段文本） */
	origin: number
	/** 本页起始字符（含，整段坐标） */
	from: number
	/** 本页结束字符（含，整段坐标） */
	to: number
}

/** 实测逐行断点排版数据（APP 端经 StaticLayout 引擎直读，条件编译；其余端不产生此数据） */
export type ParaLineLayout = {
	/** 每段行数 */
	lines : number[]
	/** 每段逐行末字符下标（段落坐标 0-based 含端点，与 lines 对齐；行数即断点数） */
	lineEnds : number[][]
}
