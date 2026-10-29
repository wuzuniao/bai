// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 i18n.uts。

/** 语言标识 */
export type Locale = 'zh' | 'en'

/** 词典类型：key 为「模块.语义」扁平键 */
export type Dict = Map<string, string>
