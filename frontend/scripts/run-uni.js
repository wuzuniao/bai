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
 * 双构建态管理（CLI 构建与 HBuilderX 鸿蒙内置管线共存）：
 *   两套管线对项目根的要求互斥，且只能靠「文件存在性」切换——HBuilderX 编鸿蒙
 *   会加载 vite.config.js 文件本身（哪怕返回空配置也会改变其入口解析而失败，
 *   按平台条件分支无效），npm pinia 则会遮蔽 HBuilderX 内置 pinia：
 *   - H5/小程序 CLI 构建（uni-app 3 alpha 管线）需要：
 *       vite.config.js（注入 uni 插件与 uts2js 产物修复，模板见 VITE_CONFIG_TEMPLATE）
 *       + node_modules/pinia（源码标准 pinia API 依赖 npm 包解析）；
 *   - HBuilderX 鸿蒙内置管线（uni-app x）要求两者必须不存在：
 *       a) vite.config.js 存在即构建失败（"Rollup failed to resolve import /main"）；
 *       b) npm pinia 使 vendor.js 残留裸 "vue" 导入，鸿蒙 es2abc 字节码编译报
 *          "Failed to resolve OhmUrl for \"vue\"" 整包失败（内置 pinia 3.0.4 无此问题）。
 *   默认（鸿蒙兼容）态：vite.config.js 不存在（模板内嵌本脚本，删除不丢内容）、
 *   node_modules/pinia 不存在（暂存为 node_modules/pinia.bak，缺失时自动 npm 补装）。
 *   CLI 构建自动进入 H5 态，退出（含 Ctrl+C）自动还原鸿蒙态；异常残留由下次运行兜底。
 *
 * 用法（由 package.json scripts 调用）：
 *   node scripts/run-uni.js <dev|build> <h5|mp-weixin>   # H5 开发 / H5·小程序构建
 *   node scripts/run-uni.js harmony [deviceId]           # 鸿蒙编译+安装+运行
 *                                                        # （默认 127.0.0.1:5555 模拟器）
 */
const { spawn, spawnSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

// 项目根目录即源码目录（HBuilderX 布局）
const projectRoot = path.resolve(__dirname, '..')

const VITE_CONFIG = path.join(projectRoot, 'vite.config.js')
const PINIA_DIR = path.join(projectRoot, 'node_modules', 'pinia')
const PINIA_BAK = path.join(projectRoot, 'node_modules', 'pinia.bak')
// 鸿蒙构建产物（HBuilderX 编译输出，内含 hvigor 工程与 oh_modules 的大量 .ts）：
// CLI 构建的 uts 编译器会全量扫描 frontend 下 .ts，扫到这些鸿蒙产物即报
// "@kit.* / @normalized:* 模块不存在"（TS2307）导致构建失败，构建前须暂移出 frontend。
const HARMONY_PROD = path.join(projectRoot, 'unpackage', 'dist', 'dev', 'app-harmony')
// 暂存目录：frontend 外（避开 uts 扫描）、frontend 同盘（保证 rename 原子）、不污染 git
const HARMONY_STASH = path.resolve(projectRoot, '..', '.harmony-stash-bai')
// HBuilderX CLI（鸿蒙编译入口）；鸿蒙目标设备默认为 DevEco 模拟器
const HX_CLI = 'C:/HBuilderX/cli.exe'
const DEFAULT_HARMONY_DEVICE = '127.0.0.1:5555'

const exists = (p) => fs.existsSync(p)

// vite.config.js 模板（仅 CLI 构建期间由本脚本生成，结束自动删除）。
// 内嵌于此避免与磁盘模板形成双真源；请勿手工编辑生成产物。
const VITE_CONFIG_TEMPLATE = `import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * 【由 scripts/run-uni.js 自动生成与管理，请勿手工编辑】
 * 仅存在于 CLI 构建（H5/小程序）期间：uni-app 3 alpha 管线需要本文件注入
 * uni 插件与 uts2js 产物修复；构建结束自动删除——HBuilderX 编译鸿蒙时本文件
 * 存在本身即导致构建失败（详见 run-uni.js 头部「双构建态管理」）。
 * 注意：uni 插件须静态导入（动态 import 的 default 解构在 uni CLI 加载本文件时
 * 报 "uni is not a function"）。
 */

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
        /Object\\.defineProperty\\(([^,]+), ([^,]+), new UTSJSONObject\\((\\{[^)]*\\})\\)\\)/g,
        'Object.defineProperty($1, $2, $3)'
      )
    },
  }
}

/**
 * 修复 H5/小程序 CLI 管线（uts2js）不擦除类型导入的缺陷：
 * 共享类型抽离在 *Defs.ts（HBuilderX 鸿蒙管线的硬性要求），但 CLI 的 UTS
 * 编译器对「import type {...} from *Defs.ts」与「值+类型混导」均不做类型
 * 擦除，rollup 解析时报 "T is not exported by ..."（实测 93 处）。
 * 此处扫描 *Defs.ts 生成类型名单，在转译产物进入 rollup 前剔除类型导入成员。
 */
/** @returns {import('vite').Plugin} */
function stripUtsTypeImports() {
  const typeNames = new Set()
  const walk = (dir) => {
    let entries = []
    try {
      entries = readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      if (e.name === 'node_modules' || e.name === 'unpackage' || e.name === 'dist') continue
      const p = join(dir, e.name)
      if (e.isDirectory()) {
        walk(p)
      } else if (e.name.endsWith('Defs.ts')) {
        const src = readFileSync(p, 'utf8')
        for (const m of src.matchAll(/export\\s+(?:type|interface)\\s+(\\w+)/g)) {
          typeNames.add(m[1])
        }
      }
    }
  }
  walk(process.cwd())
  return {
    name: 'strip-uts-type-imports',
    enforce: 'post',
    transform(code, id) {
      if (typeNames.size === 0 || code.indexOf('import') < 0) {
        return null
      }
      let changed = false
      // 1) 纯类型导入（import type {...} from '...'）整句删除（含多行子句）
      let out = code.replace(
        /import\\s+type\\s*\\{[^}]*\\}\\s*from\\s*['"][^'"]*['"];?/g,
        () => {
          changed = true
          return ''
        }
      )
      // 2) 混导子句剔除类型成员；剔除后为空则整句删除
      out = out.replace(/import\\s*\\{([^}]*)\\}\\s*from\\s*(['"])([^'"]*)\\2/g, (m, names, q, from) => {
        const parts = names.split(',').map((s) => s.trim()).filter(Boolean)
        const kept = parts.filter((p) => !typeNames.has(p.replace(/^type\\s+/, '').trim()))
        if (kept.length === parts.length) {
          return m
        }
        changed = true
        return kept.length ? 'import { ' + kept.join(', ') + ' } from ' + q + from + q : ''
      })
      return changed ? out : null
    },
  }
}

export default defineConfig(() => {
  return {
    plugins: [uni(), fixUtsScriptSetupDescriptor(), stripUtsTypeImports()],
    root: '.',
  }
})
`

// 暂移鸿蒙构建产物（逐子项：app-harmony 目录可能被 HBuilderX 文件监听锁定，整目录 rename 会失败）。
// 单项被锁（EPERM/EBUSY，如 hvigor daemon 持有的 .hvigor 缓存）则跳过——非 .ts 源目录，不阻碍 CLI 构建。
function stashHarmonyBuild() {
  if (!exists(HARMONY_PROD)) return
  const stashDir = path.join(HARMONY_STASH, 'app-harmony')
  fs.mkdirSync(stashDir, { recursive: true })
  let moved = 0
  for (const name of fs.readdirSync(HARMONY_PROD)) {
    const dst = path.join(stashDir, name)
    if (exists(dst)) continue
    try {
      fs.renameSync(path.join(HARMONY_PROD, name), dst)
      moved++
    } catch {
      console.log(`[run-uni] 跳过被锁定的鸿蒙产物子项: ${name}`)
    }
  }
  if (moved) console.log('[run-uni] 已暂存鸿蒙构建产物（构建后自动恢复）')
}

// 恢复鸿蒙构建产物（逐子项搬回后清理暂存目录）
function restoreHarmonyBuild() {
  const stashDir = path.join(HARMONY_STASH, 'app-harmony')
  if (!exists(stashDir)) return
  fs.mkdirSync(HARMONY_PROD, { recursive: true })
  for (const name of fs.readdirSync(stashDir)) {
    const dst = path.join(HARMONY_PROD, name)
    if (exists(dst)) continue
    try {
      fs.renameSync(path.join(stashDir, name), dst)
    } catch {
      console.log(`[run-uni] 鸿蒙产物子项恢复失败（保留于暂存区）: ${name}`)
    }
  }
  try {
    fs.rmdirSync(stashDir)
    fs.rmdirSync(HARMONY_STASH)
  } catch {}
  console.log('[run-uni] 已恢复鸿蒙构建产物')
}

// 进入 H5 态：生成 vite.config.js + 确保 npm pinia 存在（幂等）
function toH5State() {
  if (!exists(VITE_CONFIG)) {
    fs.writeFileSync(VITE_CONFIG, VITE_CONFIG_TEMPLATE)
    console.log('[run-uni] 已生成 vite.config.js（CLI 构建态）')
  }
  if (!exists(PINIA_DIR)) {
    if (exists(PINIA_BAK)) {
      fs.renameSync(PINIA_BAK, PINIA_DIR)
      console.log('[run-uni] 已恢复 node_modules/pinia（CLI 构建态）')
    } else {
      console.log('[run-uni] node_modules/pinia 缺失，npm 补装...')
      const r = spawnSync(
        'npm',
        ['install', 'pinia@2.3.1', '--no-save', '--no-audit', '--no-fund', '--force'],
        { shell: true, stdio: 'inherit', cwd: projectRoot }
      )
      if (r.status !== 0 || !exists(PINIA_DIR)) {
        console.error('[run-uni] pinia 补装失败，无法进行 CLI 构建')
        process.exit(1)
      }
    }
  }
  stashHarmonyBuild()
}

// 还原鸿蒙态：删除 vite.config.js + 暂存 npm pinia + 恢复鸿蒙产物（幂等）
function toHarmonyState() {
  if (exists(VITE_CONFIG)) {
    fs.unlinkSync(VITE_CONFIG)
    console.log('[run-uni] 已移除 vite.config.js（还原鸿蒙兼容态）')
  }
  if (exists(PINIA_DIR)) {
    if (exists(PINIA_BAK)) fs.rmSync(PINIA_BAK, { recursive: true, force: true })
    fs.renameSync(PINIA_DIR, PINIA_BAK)
    console.log('[run-uni] 已暂存 node_modules/pinia → pinia.bak（还原鸿蒙兼容态）')
  }
  restoreHarmonyBuild()
}

const [, , cmd, ...rest] = process.argv

// ---- CLI 构建：dev / build（h5、mp-weixin）----
if (cmd === 'dev' || cmd === 'build') {
  const platform = rest[0]
  if (!platform) {
    console.error('用法: node scripts/run-uni.js <dev|build> <h5|mp-weixin>')
    process.exit(1)
  }

  // uni CLI 参数：dev 模式无子命令，build 模式为 `build`
  const args = cmd === 'build' ? ['build', '-p', platform] : ['-p', platform]

  // 小程序产物输出到 HBuilderX 标准目录（微信开发者工具导入 unpackage/dist/build/mp-weixin 上传）；
  // H5 保持默认 dist/build/h5（scripts/deploy.sh 服务器构建依赖该路径），不得全局改输出目录
  const env = { ...process.env, UNI_INPUT_DIR: projectRoot }
  if (platform === 'mp-weixin') {
    env.UNI_OUTPUT_DIR = path.resolve(projectRoot, 'unpackage/dist/build/mp-weixin')
  }

  // 退出（含 Ctrl+C 触发的 SIGINT/SIGTERM）一律还原鸿蒙兼容态，防残留破坏 HBuilderX 编译。
  // 注意：须在 toH5State() 之前注册，切态中途抛错也能还原。
  process.on('exit', toHarmonyState)
  const forward = (sig) => () => {
    try { child.kill(sig) } catch {}
    process.exit(sig === 'SIGINT' ? 130 : 143)
  }
  process.on('SIGINT', forward('SIGINT'))
  process.on('SIGTERM', forward('SIGTERM'))

  toH5State()

  const uniBin = require.resolve('@dcloudio/vite-plugin-uni/bin/uni.js')
  const child = spawn(process.execPath, [uniBin, ...args], {
    cwd: projectRoot,
    stdio: 'inherit',
    env,
  })

  child.on('exit', (code) => process.exit(code ?? 0))

// ---- 鸿蒙：编译 + 安装 + 运行（HBuilderX CLI）----
} else if (cmd === 'harmony') {
  const deviceId = rest[0] || DEFAULT_HARMONY_DEVICE
  if (!exists(HX_CLI)) {
    console.error(`未找到 HBuilderX CLI: ${HX_CLI}`)
    process.exit(1)
  }

  // 清理 CLI 构建残留，确保鸿蒙兼容态（幂等）
  toHarmonyState()

  // cli launch 成功后进入 hilog 日志跟随模式不会退出，故流式读取输出，
  // 检测到「运行成功/失败」标志即结束（超时兜底防真卡死）
  const child = spawn(HX_CLI, ['launch', 'app-harmony', '--project', projectRoot, '--deviceId', deviceId], {
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let buf = ''
  let done = false
  const timer = setTimeout(() => {
    if (!done) {
      console.error('\n[run-uni] 鸿蒙编译超时（15 分钟未出结果），已中止')
      child.kill()
      process.exit(1)
    }
  }, 15 * 60 * 1000)
  const finish = (ok, msg) => {
    if (done) return
    done = true
    clearTimeout(timer)
    child.kill()
    console.log(`\n[run-uni] 鸿蒙${msg}`)
    process.exit(ok ? 0 : 1)
  }
  const onChunk = (d) => {
    buf += d.toString('utf8')
    process.stdout.write(d)
    if (/运行成功/.test(buf)) finish(true, '编译+安装+运行成功')
    else if (/Build failed|构建失败|编译失败|安装失败|运行失败/.test(buf)) finish(false, '构建失败（详见上方输出）')
  }
  child.stdout.on('data', onChunk)
  child.stderr.on('data', onChunk)
  child.on('exit', (code) => {
    if (!done) {
      done = true
      clearTimeout(timer)
      console.error(`\n[run-uni] cli 提前退出（code=${code}），未检测到成功标志`)
      process.exit(code ?? 1)
    }
  })

// ---- 未知命令 ----
} else {
  console.error(
    '用法:\n' +
      '  node scripts/run-uni.js <dev|build> <h5|mp-weixin>   # H5 开发 / H5·小程序构建\n' +
      '  node scripts/run-uni.js harmony [deviceId]           # 鸿蒙编译+安装+运行'
  )
  process.exit(1)
}
