const l = require('lucide-react')
const fs = require('fs')
const path = require('path')
const names = new Set()
function walk(d) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f)
    if (fs.statSync(p).isDirectory()) walk(p)
    else if (f.endsWith('.tsx') || f.endsWith('.ts')) {
      const src = fs.readFileSync(p, 'utf8')
      const m = src.match(/import\s*\{([^}]+)\}\s*from\s*'lucide-react'/g)
      if (m) for (const block of m) {
        const inner = block.match(/\{([^}]+)\}/)[1]
        for (const n of inner.split(',')) {
          const name = n.trim().split(/\s+as\s+/)[0].trim()
          if (name) names.add(name)
        }
      }
    }
  }
}
walk('src')
const missing = [...names].filter((n) => typeof l[n] === 'undefined')
console.log('total icons used:', names.size)
console.log('MISSING:', JSON.stringify(missing))
