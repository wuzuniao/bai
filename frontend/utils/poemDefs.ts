// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 poem.uts。

/** 字单元（拼音 + 汉字） */
export type PoemChar = {
	char: string
	pinyin: string
}

/** 诗行（7 字单元 + 行尾标点） */
export type PoemLine = {
	chars: PoemChar[]
	punct: string
}
