// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 layout.uts。

/** 小程序胶囊按钮矩形（避让计算源） */
export type CapsuleRect = {
	/** 胶囊顶边（px） */
	top : number
	/** 胶囊左缘（px） */
	left : number
	/** 胶囊高度（px） */
	height : number
}
