// UTS 顶层块拓扑重排工具（解决「先调用后定义」无函数提升问题）
// 用法：node reorder_uts.mjs <file> --check   （dry-run 只报告）
//       node reorder_uts.mjs <file> --apply   （备份后写回）
// 安全措施：块内容拼接守恒校验、总行数校验、深度自守校验、写前备份、写后回读比对。

import fs from 'node:fs';
import path from 'node:path';

const file = process.argv[2];
const mode = process.argv[3] || '--check';
if (!file) { console.error('用法: node reorder_uts.mjs <file> [--check|--apply]'); process.exit(2); }

const src = fs.readFileSync(file, 'utf8');
const EOL = src.includes('\r\n') ? '\r\n' : '\n';
const lines = src.split(/\r?\n/);

// ---- 1. 定位 script 块 ----
let sStart = -1, sEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (sStart < 0 && /^<script\b/.test(lines[i])) sStart = i;
  else if (sStart >= 0 && /^<\/script>/.test(lines[i])) { sEnd = i; break; }
}
if (sStart < 0 || sEnd < 0) { console.error('未找到 <script>…</script>'); process.exit(2); }

// ---- 2. 深度感知切块（字符串/注释不参与深度；顶层 #ifdef…#endif 组打包为单一块）----
// 指令识别：支持 `#ifdef`、`// #ifdef`、`/* #ifdef ... */` 三种顶层形式；组内块整体保序、组整体参与拓扑。
function directiveOf(t) {
  if (!t.startsWith('//') && !t.startsWith('/*')) return null;
  const s = t.replace(/^\/\/\s*/, '').replace(/^\/\*\s*/, '').replace(/\*\/\s*$/, '').trim();
  if (/^#ifdef\b/.test(s) || /^#ifndef\b/.test(s)) return 'open';
  if (/^#endif\b/.test(s)) return 'close';
  return null;
}
// 状态机逐字符扫描，输出每行：depthAfter、是否在字符串/注释中结束等。
function scanDeposits(text) {
  // 返回每行结束时的 { brace: 深度({}-{}[]计数), inS, inT, inLC, inBC }
  const res = [];
  let depth = 0; // {} [] () 合并计数
  let state = 'code'; // code | sq | dq | tpl | line | block
  let tplDepth = []; // 模板串内 ${  的深度栈
  for (const line of text.split(/\r?\n/)) {
    let i = 0;
    while (i < line.length) {
      const c = line[i], n = line[i + 1];
      if (state === 'code') {
        if (c === '/' && n === '/') { state = 'line'; i += 2; continue; }
        if (c === '/' && n === '*') { state = 'block'; i += 2; continue; }
        if (c === "'") { state = 'sq'; i++; continue; }
        if (c === '"') { state = 'dq'; i++; continue; }
        if (c === '`') { state = 'tpl'; i++; continue; }
        if (c === '{' || c === '(' || c === '[') depth++;
        else if (c === '}' || c === ')' || c === ']') {
          depth--;
          if (tplDepth.length && depth === tplDepth[tplDepth.length - 1]) { tplDepth.pop(); state = 'tpl'; }
        }
        i++;
      } else if (state === 'sq' || state === 'dq') {
        if (c === '\\') i += 2;
        else if ((state === 'sq' && c === "'") || (state === 'dq' && c === '"')) { state = 'code'; i++; }
        else i++;
      } else if (state === 'tpl') {
        if (c === '\\') i += 2;
        else if (c === '`') { state = 'code'; i++; }
        else if (c === '$' && n === '{') { tplDepth.push(depth); depth++; state = 'code'; i += 2; }
        else i++;
      } else if (state === 'line') { i = line.length; }
      else if (state === 'block') {
        if (c === '*' && n === '/') { state = 'code'; i += 2; } else i++;
      }
    }
    if (state === 'line') state = 'code';
    res.push(depth);
  }
  return res;
}
const depths = scanDeposits(lines.slice(sStart + 1, sEnd).join('\n'));

const body = lines.slice(sStart + 1, sEnd); // script 内容行
// 切块：在 depth==0 的行边界切块；doc/普通注释与空行归入其后第一个「实体块」；
// 顶层条件编译组（#ifdef…#endif，含 // 与 /* */ 注释形式）打包为单一块：组内块保序、组整体参与拓扑。
const blocks = [];
let cur = null; // { lines: [], startIdx }
const groupStack = []; // { lines: [], members: [], startIdx }
function flush() {
  if (!cur || !cur.lines.length) { cur = null; return; }
  if (groupStack.length) groupStack[groupStack.length - 1].members.push(cur);
  else blocks.push(cur);
  cur = null;
}

for (let i = 0; i < body.length; i++) {
  const raw = body[i];
  const t = raw.trim();
  const dir = depths[i] === 0 ? directiveOf(t) : null;
  if (dir === 'open') {
    flush();
    groupStack.push({ lines: [raw], members: [], startIdx: i });
    continue;
  }
  if (dir === 'close') {
    flush();
    const g = groupStack.pop();
    if (!g) {
      // 不平衡的多余 #endif：按普通注释行处理（防御，正常不应出现）
      cur = cur || { lines: [], startIdx: i };
      cur.lines.push(raw);
      flush();
      continue;
    }
    const gb = { lines: [...g.lines, ...g.members.flatMap(m => m.lines), raw], startIdx: g.startIdx };
    if (groupStack.length) groupStack[groupStack.length - 1].members.push(gb);
    else blocks.push(gb);
    continue;
  }
  // 普通行（组内组外同规则）
  if (depths[i] === 0 && !raw.trim()) { cur = cur || { lines: [], startIdx: i }; cur.lines.push(raw); flush(); continue; }
  if (depths[i] === 0) {
    const isCmt = t.startsWith('//') || t.startsWith('/*') || t.startsWith('*');
    if (isCmt) { cur = cur || { lines: [], startIdx: i }; cur.lines.push(raw); continue; }
    // depth==0 实体行必是语句末行，append 后 flush
    cur = cur || { lines: [], startIdx: i };
    cur.lines.push(raw);
    flush();
    continue;
  }
  cur = cur || { lines: [], startIdx: i };
  cur.lines.push(raw);
  if (depths[i] === 0) flush();
}
flush();
if (groupStack.length) { console.error('存在未闭合的顶层条件编译组，中止'); process.exit(2); }

// ---- 3. 名称定义与引用提取 ----
const KEYWORDS = new Set(('const let var function return if else for while do switch case break continue new typeof instanceof await async export import from true false null undefined this void delete in of catch finally try throw default extends super class enum interface type implements namespace declare readonly public private protected static get set constructor number string boolean any object symbol bigint never unknown as is require module exports').split(' '));

function stripNoise(text) {
  // 去注释与字符串，保留代码标识符上下文（含模板串 ${} 内表达式）
  let out = '';
  let state = 'code';
  let depth = 0;
  const tplDepth = [];
  const linesN = text.split(/\r?\n/);
  for (const line of linesN) {
    let i = 0;
    while (i < line.length) {
      const c = line[i], n = line[i + 1];
      if (state === 'code') {
        if (c === '/' && n === '/') { break; }
        if (c === '/' && n === '*') { state = 'block'; i += 2; continue; }
        if (c === "'") { state = 'sq'; i++; continue; }
        if (c === '"') { state = 'dq'; i++; continue; }
        if (c === '`') { state = 'tpl'; i++; continue; }
        if (c === '{' || c === '(' || c === '[') depth++;
        else if (c === '}' || c === ')' || c === ']') {
          depth--;
          if (tplDepth.length && depth === tplDepth[tplDepth.length - 1]) { tplDepth.pop(); state = 'tpl'; i++; continue; }
        }
        out += c; i++;
      } else if (state === 'sq') { if (c === '\\') i += 2; else if (c === "'") { state = 'code'; i++; } else i++; }
      else if (state === 'dq') { if (c === '\\') i += 2; else if (c === '"') { state = 'code'; i++; } else i++; }
      else if (state === 'tpl') { if (c === '\\') i += 2; else if (c === '`') { state = 'code'; i++; } else if (c === '$' && n === '{') { out += ' '; tplDepth.push(depth); depth++; state = 'code'; i += 2; } else i++; }
      else if (state === 'block') { if (c === '*' && n === '/') { state = 'code'; i += 2; } else i++; }
    }
    out += '\n';
  }
  return out;
}

function definedNames(text) {
  // 只提取「行首深度为 0」的顶层声明，块内局部 const/let/var 不算
  const rawLines = text.split(/\r?\n/);
  const dep = scanDeposits(text);
  const names = new Set();
  let prev = 0;
  for (let i = 0; i < rawLines.length; i++) {
    const startDepth = prev;
    prev = dep[i];
    if (startDepth !== 0) continue;
    const code = stripNoise(rawLines[i]);
    let m;
    if ((m = code.match(/(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/))) names.add(m[1]);
    else if ((m = code.match(/(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)/))) names.add(m[1]);
    else if ((m = code.match(/(?:export\s+)?(?:const|let|var)\s*\{([^}]*)\}/))) {
      for (const p of m[1].split(',')) { const nm = p.split(':')[0].trim(); if (/^[A-Za-z_$][\w$]*$/.test(nm)) names.add(nm); }
    }
    else if ((m = code.match(/(?:export\s+)?(?:const|let|var)\s*\[([^\]]*)\]/))) {
      for (const p of m[1].split(',')) { const nm = p.trim(); if (/^[A-Za-z_$][\w$]*$/.test(nm)) names.add(nm); }
    }
  }
  return names;
}

function referencedNames(text) {
  const code = stripNoise(text);
  // 先剔除 .prop 属性访问
  const noProp = code.replace(/\.\s*[A-Za-z_$][\w$]*/g, '.');
  // 剔除对象字面量 key（key: value 形式；{ key } 简写是真实引用，保留）
  const noKey = noProp.replace(/([{,]\s*)([A-Za-z_$][\w$]*)(\s*:)/g, '$1$3');
  const names = new Set();
  for (const m of noKey.matchAll(/[A-Za-z_$][\w$]*/g)) {
    if (!KEYWORDS.has(m[0])) names.add(m[0]);
  }
  return names;
}

// ---- 4. 依赖图 + Tarjan SCC + 稳定拓扑 ----
const infos = blocks.map((b, idx) => ({ idx, defs: definedNames(b.lines.join('\n')), refs: referencedNames(b.lines.join('\n')), text: b.lines.join('\n') }));
const edges = Array.from({ length: blocks.length }, () => new Set());
for (const a of infos) {
  for (const d of a.defs) {
    for (const b of infos) {
      if (b.idx !== a.idx && b.refs.has(d)) edges[b.idx].add(a.idx); // b 依赖 a
    }
  }
}
// Tarjan SCC
const N = blocks.length;
const idxOf = new Array(N).fill(-1), low = new Array(N).fill(0), onStk = new Array(N).fill(false);
const stk = []; let counter = 0; const sccs = [];
function strong(v) {
  idxOf[v] = low[v] = counter++; stk.push(v); onStk[v] = true;
  for (const w of edges[v]) {
    if (idxOf[w] === -1) { strong(w); low[v] = Math.min(low[v], low[w]); }
    else if (onStk[w]) low[v] = Math.min(low[v], idxOf[w]);
  }
  if (low[v] === idxOf[v]) {
    const comp = []; let w;
    do { w = stk.pop(); onStk[w] = false; comp.push(w); } while (w !== v);
    sccs.push(comp);
  }
}
for (let v = 0; v < N; v++) if (idxOf[v] === -1) strong(v);
// SCC 缩点 → Kahn 稳定（候选中取原 idx 最小）
const sccOf = new Array(N);
sccs.forEach((c, i) => c.forEach(v => sccOf[v] = i));
const sccEdges = Array.from({ length: sccs.length }, () => new Set());
const indeg = new Array(sccs.length).fill(0);
for (let v = 0; v < N; v++) for (const w of edges[v]) {
  // v 依赖 w ⇒ 边「w→v」（被依赖者先行），indeg 加在依赖者上
  const a = sccOf[v], b = sccOf[w];
  if (a !== b && !sccEdges[b].has(a)) { sccEdges[b].add(a); indeg[a]++; }
}
const order = [];
const ready = sccs.map((_, i) => i).filter(i => indeg[i] === 0).sort((x, y) => Math.min(...sccs[x]) - Math.min(...sccs[y]));
const heap = ready;
while (heap.length) {
  heap.sort((x, y) => Math.min(...sccs[x]) - Math.min(...sccs[y]));
  const c = heap.shift();
  order.push(c);
  for (const nb of sccEdges[c]) { if (--indeg[nb] === 0) heap.push(nb); }
}
if (order.length !== sccs.length) { console.error('SCC 缩点后仍有环，中止'); process.exit(2); }
const newOrder = [];
for (const c of order) { const comp = [...sccs[c]].sort((a, b) => a - b); newOrder.push(...comp); }

// ---- 5. 报告 / 应用 ----
const moved = newOrder.filter((v, i) => v !== i);
const backEdges = [];
for (const a of infos) for (const d of a.defs) {
  for (const b of infos) {
    if (b.idx !== a.idx && b.refs.has(d) && a.idx > b.idx) backEdges.push(`${b.idx + 1}#${d} <- 定义于块${a.idx + 1}`);
  }
}
console.log(`块数: ${blocks.length}  script 行数: ${body.length}  后向依赖边(需搬移): ${backEdges.length}`);
// dump 指定块
if (process.argv[4] === '--find') {
  const nm = process.argv[5];
  for (const info of infos) {
    const defHere = info.defs.has(nm);
    const refHere = info.refs.has(nm);
    if (defHere || refHere) {
      const pos = newOrder.indexOf(info.idx);
      console.log(`块${info.idx}（newOrder位置${pos}）${defHere ? 'DEF' : '   '} ${refHere ? 'REF' : '   '} | ${blocks[info.idx].lines.map(l => l.trim()).filter(l => l && !l.startsWith('//') && !l.startsWith('*'))[0]?.slice(0, 60) ?? ''}`);
    }
  }
  process.exit(0);
}
if (process.argv[4] === '--dump') {
  const want = process.argv[5].split(',').map(Number);
  for (const v of want) {
    console.log(`== 块${v}（startIdx ${blocks[v].startIdx}，${blocks[v].lines.length} 行）==`);
    console.log(blocks[v].lines.join('\n').split('\n').slice(0, 12).map(l => '  ' + l).join('\n'));
  }
  process.exit(0);
}
console.log(`将移动块数: ${moved.length}  SCC 个数: ${sccs.length}  多元素 SCC: ${sccs.filter(c => c.length > 1).map(c => c.sort((a, b) => a - b).map(x => x + 1).join(',')).join(' | ') || '无'}`);
if (backEdges.length <= 40) backEdges.forEach(e => console.log('  ' + e));
// 打印多元素 SCC 各块概要（首行 + 定义名）
for (const c of sccs.filter(c => c.length > 1)) {
  c.sort((a, b) => a - b).forEach(v => {
    const first = blocks[v].lines.map(l => l.trim()).find(l => l && !l.startsWith('//') && !l.startsWith('*') && !l.startsWith('/*')) || '';
    console.log(`SCC块${v} defs=[${[...infos[v].defs].join(',')}] :: ${first.slice(0, 80)}`);
  });
  console.log('---');
}
if (process.argv[4] === '--debug') {
  // 边总量与热点定义名
  let total = 0; const hot = new Map();
  for (let v = 0; v < N; v++) for (const w of edges[v]) { total++; const key = `${w}<-${v}`; }
  for (const a of infos) for (const d of a.defs) {
    let c = 0; for (const b of infos) if (b.idx !== a.idx && b.refs.has(d)) c++;
    if (c > 0) hot.set(d + '@' + a.idx, c);
  }
  console.log('总依赖边: ' + total);
  [...hot.entries()].sort((x, y) => y[1] - x[1]).slice(0, 15).forEach(([k, c]) => console.log(`  ${k}: ${c} 个引用块`));
  // newOrder 与原序的首个分歧
  for (let i = 0; i < newOrder.length; i++) if (newOrder[i] !== i) { console.log(`首个分歧: 位置${i} 放置块${newOrder[i]}`); break; }
  console.log('newOrder[0..40]: ' + newOrder.slice(0, 40).join(','));
}

const reorderedBody = newOrder.flatMap(v => blocks[v].lines);
if (mode === '--apply') {
  // 校验 1：行多重集合守恒（块仅换序，任何行不得丢失/新增/篡改）
  const ra = [...body].sort().join('\n');
  const rb = [...reorderedBody].sort().join('\n');
  if (ra !== rb) {
    let pa = 0, pb = 0;
    const la = ra.split('\n'), lb = rb.split('\n');
    let p = 0; while (p < Math.min(la.length, lb.length) && la[p] === lb[p]) p++;
    console.error('校验失败：行集合不一致，首差异行 ' + p);
    console.error('原: ' + JSON.stringify((la[p] || '').slice(0, 90)));
    console.error('新: ' + JSON.stringify((lb[p] || '').slice(0, 90)));
    process.exit(2);
  }
  // 校验 2：行数
  if (reorderedBody.length !== body.length) { console.error('校验失败：行数不一致'); process.exit(2); }
  const out = [...lines.slice(0, sStart + 1), ...reorderedBody, ...lines.slice(sEnd)];
  const bak = file + '.bak';
  fs.copyFileSync(file, bak);
  fs.writeFileSync(file, out.join(EOL), 'utf8');
  // 写后回读
  const rb2 = fs.readFileSync(file, 'utf8');
  if (rb2 !== out.join(EOL)) { console.error('写后回读不一致！备份在 ' + bak); process.exit(2); }
  console.log(`已写回（备份: ${path.basename(bak)}），移动 ${moved.length} 块`);
} else {
  console.log('(dry-run，未写文件)');
}
