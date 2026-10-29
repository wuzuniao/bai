// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 announcement.uts。

/** 公告条目（列表接口返回项） */
export type AnnouncementItem = {
	id: number
	title: string
	content: string
	created_at: string
	updated_at: string
	is_read: boolean
}

/** 公告分页结果 */
export type AnnouncementsPage = {
	items: AnnouncementItem[]
	hasMore: boolean
	unreadCount: number
}
