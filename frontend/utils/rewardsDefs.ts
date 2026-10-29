// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 rewards.uts。

export type RewardTier = {
	/** 档位阈值分钟数 */
	minutes: number
	/** 徽标文案（5'/30'/2h/6h/12h） */
	badge: string
	/** 标题 i18n key（渲染层 t(title) 取词） */
	title: string
	/** 基础奖励铜币数 */
	base: number
	/** 额外赠送铜币数 */
	bonus: number
}
