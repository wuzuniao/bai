import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// HBuilderX 标准布局（源码位于项目根目录，无 src 层），
// CLI 构建与 HBuilderX「运行/发行」共用同一套目录结构（UNI_INPUT_DIR 由 run-uni.js 注入）。

/**
 * 修复 uts2js（H5/小程序端）编译器的 script-setup 产物缺陷：
 * __isScriptSetup 的 defineProperty 描述符被错误生成为 new UTSJSONObject({...})，
 * 其属性实现为访问器，运行时 Object.defineProperty 报
 * 「Invalid property descriptor. Cannot both specify accessors and a value or writable attribute」，
 * 导致 setup 崩溃、页面无法挂载（H5 端整站白屏）。此处改回普通对象描述符。
 */
/** @returns {import('vite').Plugin} */
function fixUtsScriptSetupDescriptor() {
  const BAD = 'new UTSJSONObject({ enumerable: false, value: true })'
  return {
    name: 'fix-uts-script-setup-descriptor',
    enforce: 'post',
    transform(code, id) {
      if (code.indexOf(BAD) < 0) {
        return null
      }
      return code.replace(
        /Object\.defineProperty\(([^,]+), ([^,]+), new UTSJSONObject\((\{[^)]*\})\)\)/g,
        'Object.defineProperty($1, $2, $3)'
      )
    },
  }
}

export default defineConfig(() => {
  return {
    plugins: [uni(), fixUtsScriptSetupDescriptor()],
    root: '.',
  }
})
