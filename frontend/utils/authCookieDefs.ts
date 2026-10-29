// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 authCookie.uts。

/** 同步登录态的入参（传入的为项目令牌；内部交换平台令牌后写 Cookie） */
export type SyncAuthCookieOptions = {
	access_token: string
	/** 项目 refresh_token（交换用不到，仅兼容调用点签名） */
	refresh_token: string
	/** 项目 access_token 有效期（秒）；<=0 时用缺省 TTL（仅作兜底） */
	expires_in: number
	/** 用户信息 JSON 字符串（可选）；缺省时保留 Cookie 旧值 */
	userInfoJson?: string
}

/** 恢复成功回调入参（项目令牌 + 资料 JSON 字符串，写入本地 storage） */
export type RestoredAuthState = {
	access_token: string
	refresh_token: string
	/** 项目身份资料 JSON 字符串（GET /users/info 的 data，可能为空串） */
	userInfoJson: string
}
