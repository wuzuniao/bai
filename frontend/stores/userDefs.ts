// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 user.uts（Pinia store）。

/** 用户信息结构 */
export type UserInfo = {
	id: number
	username: string
	signature: string
	/** 头像标识（数据库存 key，前端映射到 static 头像图） */
	avatar_url: string
	email: string
	/** 是否已设置密码（微信登录用户可能无密码） */
	has_password: boolean
	/** 1-正常，0-待删除 */
	status: number
	/** 全局角色编码数组（如 ["admin"]），空数组=普通用户 */
	roles: string[]
}
