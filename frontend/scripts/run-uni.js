/**
 * uni-app CLI 启动包装脚本（与 yao 项目同构）
 * --------------------------------------------------------------------------
 * 背景：
 *   工程为 HBuilderX 标准布局（源码直接位于 frontend/ 根目录，无 src 层），
 *   以便使用 HBuilderX 发行 App / iOS / 多端小程序。
 *   而 uni-app CLI 默认把输入目录写死为 <项目根>/src（见 vite-plugin-uni 的
 *   cli/build.js: `const inputDir = process.env.UNI_INPUT_DIR`，未设置时由 CLI
 *   默认填充为 src），会导致 CLI 构建报 "ENOENT: ... src/manifest.json"。
 *
 * 作用：
 *   1. 在调用 uni CLI 前把 UNI_INPUT_DIR 指向项目根目录，使 CLI 与 HBuilderX
 *      共用同一套目录结构，两种构建方式并存。
 *
 * 用法（由 package.json scripts 调用）：
 *   node scripts/run-uni.js <dev|build> <platform>
 *   例：node scripts/run-uni.js build h5
 */
const { spawn } = require('node:child_process')
const path = require('node:path')

const [, , mode, platform] = process.argv

if (!mode || !platform) {
  console.error('用法: node scripts/run-uni.js <dev|build> <platform>')
  process.exit(1)
}

if (mode !== 'dev' && mode !== 'build') {
  console.error(`不支持的模式: ${mode}（仅支持 dev 或 build）`)
  process.exit(1)
}

// 项目根目录即源码目录（HBuilderX 布局）
const projectRoot = path.resolve(__dirname, '..')

// uni CLI 参数：dev 模式无子命令，build 模式为 `build`
const args = mode === 'build' ? ['build', '-p', platform] : ['-p', platform]

// 小程序产物输出到 HBuilderX 标准目录（微信开发者工具导入 unpackage/dist/build/mp-weixin 上传）；
// H5 保持默认 dist/build/h5（scripts/deploy.sh 服务器构建依赖该路径），不得全局改输出目录
const env = {
  ...process.env,
  UNI_INPUT_DIR: projectRoot,
}
if (platform === 'mp-weixin') {
  env.UNI_OUTPUT_DIR = path.resolve(projectRoot, 'unpackage/dist/build/mp-weixin')
}

const uniBin = require.resolve('@dcloudio/vite-plugin-uni/bin/uni.js')

const child = spawn(process.execPath, [uniBin, ...args], {
  cwd: projectRoot,
  stdio: 'inherit',
  env,
})

child.on('exit', (code) => process.exit(code ?? 0))
