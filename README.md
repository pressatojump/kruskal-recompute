# kruskal-recompute

A sealed, machine-discovered Kruskal minimum-spanning-tree implementation you can
recompute yourself — no trust required.

**Live page:** https://pressatojump.github.io/kruskal-recompute/

The page embeds discovery `gen_kruskal_6cc52bf5` (from a sealed automated
program-search catalog, 3632 records, sandbox-verified at seal time) **byte-verbatim**:

- **code size:** 701 bytes
- **code sha256:** `e4cf92636f23e43ba2c770b9ad4a8932300d359f8803a502a038705cabf30a19`

The page hashes those bytes in your browser (WebCrypto) on every load and prints the
result next to the pinned value. The sealed code runs verbatim (only a `return`
hook is appended at runtime; the bytes are untouched) and every result is
cross-checked against an independent Prim's implementation on the same page.

## Verify from the wire (third-party, offline)

```bash
curl -o page.html https://pressatojump.github.io/kruskal-recompute/
shasum -a 256 page.html    # compare with index.sha256 in this repo

python3 - <<'PY'
import re,hashlib
h=open('page.html',encoding='utf-8').read()
code=re.search(r'id="sealed-code">(.+?)</script>',h,re.S).group(1)
print(len(code), hashlib.sha256(code.encode()).hexdigest())
# expect: 701 e4cf92636f23e43b... (full value in index.sha256 companion of the code block pin)
PY

node -e 'const s=require("fs").readFileSync("page.html","utf8");const m=s.match(/id="sealed-code">([\s\S]+?)<\/script>/);const f=(new Function(m[1]+"\n;return kruskal;"))();console.log(f(4,[[0,1,1],[0,2,2],[1,3,4],[2,3,3]]))'
# prints 6 (textbook MST weight)
```

## Full independent auditor

```bash
git clone https://github.com/pressatojump/kruskal-recompute.git
cd kruskal-recompute
python3 auditor.py            # grades the LIVE wire bytes by default
python3 auditor.py index.html # or a local copy
```

The auditor extracts the sealed block from the served bytes, hashes it, re-runs it
in Node, and recomputes MST weights with independent Python Prim's and Kruskal's
implementations across 10 published vectors and 2000 random spanning-tree-based
graphs. Exit code 0 = everything agrees.

## The 10 published vectors

| vector | n | MST weight |
|---|---|---|
| textbook4 | 4 | 6 |
| triangle | 3 | 3 |
| single-node | 1 | 0 |
| two-nodes | 2 | 7 |
| parallel-edges | 2 | 3 |
| zero-weight | 3 | 0 |
| grid-9 | 9 | 8 |
| hub-and-spoke | 4 | 3 |
| long-chain | 13 | 43 |
| dense-8 | 8 | 14 |

Zero dependencies, zero telemetry, nothing leaves your browser.
