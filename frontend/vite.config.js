import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// HBuilderX 标准布局（源码位于项目根目录，无 src 层），
// CLI 构建与 HBuilderX「运行/发行」共用同一套目录结构（UNI_INPUT_DIR 由 run-uni.js 注入）。
export default defineConfig(() => {
  return {
    plugins: [uni()],
    root: '.',
  }
})
