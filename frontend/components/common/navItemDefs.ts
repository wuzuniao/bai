// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 navItem.uts。

/** 底部导航项（导航数据与页面跳转由 BottomNavBar 统一管理，页面仅传 active） */
export type BottomNavItem = {
	/** 激活项标识（home / bookshelf / mine），与页面传入的 active 比对 */
	key: string
	/** 未激活图标路径 */
	icon: string
	/** 激活图标路径 */
	iconActive: string
	/** 图标宽（rpx） */
	iconWidth: number
	/** 图标高（rpx） */
	iconHeight: number
	/** 目标页面路径（以 / 开头） */
	path: string
}
