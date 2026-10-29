// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 request.uts。

/** 统一响应结构（code 非 0 表示业务错误，msg 面向用户） */
export type ApiResponse = {
	code: number
	msg: string
	data: UTSJSONObject | null
}

/** 请求选项 */
export type RequestOptions = {
	/** 接口路径（以 / 开头，如 /api/v1/users/login） */
	url: string
	/** 请求方法 */
	method: RequestMethod
	/** 请求体（无则为 null） */
	data: UTSJSONObject | null
	/** 是否附加 Authorization 头 */
	auth: boolean
	/** 超时毫秒数 */
	timeout: number
	/** 基础地址（缺省=auth 认证服务；业务后端传 API_BASE_URL） */
	baseUrl?: string
	/** 静默模式：401 时不跳转登录页（未登录属常态的业务接口用，由调用方容错） */
	silent?: boolean
	/** 收到 401 时不再触发静默刷新（防递归，重试请求置 true） */
	skipAuthRefresh?: boolean
}
