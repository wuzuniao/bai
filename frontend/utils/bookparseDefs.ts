// 共享类型定义抽离到 .ts：HBuilderX 5.33 的 UTS 编译器对 type-only 导入会改写为 *.ts 路径，
// 若类型仍留在 .uts 中会报“未导出”。此处仅放类型声明，运行逻辑见 bookparse.uts。

/** 同步结果统计 */
export type SyncResult = {
	/** 上传成功本数 */
	uploaded: number
	/** 下载成功本数 */
	downloaded: number
	/** 反向建档恢复本数（云端有对象而本地无书行） */
	restored: number
	/** 失败本数（单本失败不中断整体，继续同步其余） */
	failed: number
}
