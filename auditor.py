#!/usr/bin/env python3
"""Independent auditor for pressatojump/kruskal-recompute.

Grades the LIVE wire bytes of https://pressatojump.github.io/kruskal-recompute/
(default) or a local page.html copy:

  1. extracts the sealed block between id="sealed-code"> and the next </script>
  2. sha256s it -> must equal the pinned catalog seal
  3. re-runs the sealed bytes in Node (verbatim + return hook, bytes untouched)
  4. independently recomputes MST weight in pure Python (Prim's AND Kruskal's)
  5. checks 10 published vectors + 2000 random graphs
     (spanning-tree-based generator: connected by construction)
  6. verifies the page's embedded JS self-hash pin (expect-constant)

No trust in the page is required beyond the bytes you can hash yourself.
Exit code 0 = all checks pass.
"""
import hashlib, json, random, re, subprocess, sys, urllib.request

URL = "https://pressatojump.github.io/kruskal-recompute/"
PIN = "e4cf92636f23e43ba2c770b9ad4a8932300d359f8803a502a038705cabf30a19"  # gen_kruskal_6cc52bf5
EXPECT_HASH_JS = 'const EXPECT_HASH = "' + PIN + '"'

def get_page():
    if len(sys.argv) > 1:  # local file mode
        return open(sys.argv[1], encoding="utf-8").read()
    with urllib.request.urlopen(URL, timeout=30) as r:
        return r.read().decode("utf-8")

# --- independent Python MST implementations (written separately from the JS) ---
def prim_mst(n, edges):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w)); adj[v].append((u, w))
    if n == 0: return 0
    intree = [False] * n; intree[0] = True
    weight = 0
    for _ in range(n - 1):
        best = None
        for u in range(n):
            if not intree[u]: continue
            for v, w in adj[u]:
                if not intree[v] and (best is None or w < best[2]):
                    best = (u, v, w)
        if best is None: return None  # disconnected
        intree[best[1]] = True; weight += best[2]
    return weight

def kruskal_py(n, edges):
    p = list(range(n))
    def find(x):
        while p[x] != x: p[x] = p[p[x]]; x = p[x]
        return x
    weight = 0; used = 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        a, b = find(u), find(v)
        if a != b: p[a] = b; weight += w; used += 1
        if used == n - 1: break
    return weight

def connected(n, edges):
    if n <= 1: return True
    adj = [[] for _ in range(n)]
    for u, v, w in edges: adj[u].append(v); adj[v].append(u)
    seen = {0}; q = [0]
    while q:
        u = q.pop()
        for v in adj[u]:
            if v not in seen: seen.add(v); q.append(v)
    return len(seen) == n

VECTORS = [
    ("textbook4",     4,  [[0,1,1],[0,2,2],[1,3,4],[2,3,3]], 6),
    ("triangle",      3,  [[0,1,5],[0,2,1],[1,2,2]], 3),
    ("single-node",   1,  [], 0),
    ("two-nodes",     2,  [[0,1,7]], 7),
    ("parallel-edges",2,  [[0,1,9],[0,1,3],[0,1,5]], 3),
    ("zero-weight",   3,  [[0,1,0],[1,2,0],[0,2,4]], 0),
    ("grid-9",        9,  [[0,1,1],[0,3,1],[1,2,1],[1,4,5],[2,5,1],[3,4,1],[3,6,1],[4,5,1],[4,7,1],[5,8,1],[6,7,1],[7,8,1]], 8),
    ("hub-and-spoke", 4,  [[0,1,2],[0,2,3],[0,3,1],[1,2,1],[2,3,1]], 3),
    ("long-chain",    13, [[0,1,1],[1,2,2],[2,3,3],[3,4,4],[4,5,5],[5,6,6],[6,7,7],[7,8,1],[8,9,2],[9,10,3],[10,11,4],[11,12,5]], 43),
    ("dense-8",       8,  [[0,1,9],[0,2,8],[0,3,7],[0,4,6],[0,5,5],[0,6,4],[0,7,3],[1,2,3],[1,3,2],[1,4,1],[1,5,9],[1,6,8],[1,7,7],[2,3,6],[2,4,5],[2,5,4],[2,6,3],[2,7,2],[3,4,9],[3,5,8],[3,6,7],[3,7,6],[4,5,3],[4,6,2],[4,7,1],[5,6,6],[5,7,5],[6,7,9]], 14),
]

def main():
    fails = 0
    page = get_page()
    page_sha = hashlib.sha256(page.encode()).hexdigest()
    print(f"page sha256        : {page_sha}")

    m = re.search(r'id="sealed-code">(.+?)</script>', page, re.S)
    if not m:
        print("FAIL: sealed-code block not found in page"); return 1
    code = m.group(1)
    h = hashlib.sha256(code.encode()).hexdigest()
    ok = h == PIN
    print(f"sealed code bytes  : {len(code)}  sha256 {h[:16]}…")
    print(f"pin check          : {'MATCH' if ok else 'MISMATCH'}")
    fails += 0 if ok else 1

    # page must embed the same pin as its in-browser self-check
    ok2 = EXPECT_HASH_JS in page
    print(f"page self-hash pin : {'MATCH' if ok2 else 'MISMATCH'}")
    fails += 0 if ok2 else 1

    # vectors present in the page (10 named vectors)
    ok3 = all(name in page for name, _, _, _ in VECTORS)
    print(f"vectors embedded   : {'10/10 present' if ok3 else 'MISSING'}")
    fails += 0 if ok3 else 1

    # re-run the sealed bytes in Node, verbatim + return hook
    js = code + "\n;const vs=" + json.dumps(
        [{"n": n, "edges": e} for _, n, e, _ in VECTORS]) + \
        ";\nconst out=vs.map(v=>kruskal(v.n,v.edges));console.log(JSON.stringify(out));"
    try:
        res = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        got = json.loads(res.stdout.strip())
    except Exception as e:
        print("FAIL: node re-run error:", e); return 1
    for i, (name, n, edges, exp) in enumerate(VECTORS):
        p = prim_mst(n, edges)
        k = kruskal_py(n, edges)
        mark = "PASS" if got[i] == exp and p == exp and k == exp else "FAIL"
        if mark == "FAIL": fails += 1
        print(f"  {name:15s} sealed={got[i]:>3} prim={p if p is not None else 'null':>3} pykruskal={k:>3} expected={exp:>3}  {mark}")

    # random cross-check: spanning-tree-based generator (connected BY CONSTRUCTION)
    rng = random.Random(20260907)
    graphs = []
    while len(graphs) < 2000:
        n = rng.randint(2, 9)
        order = list(range(1, n)); rng.shuffle(order)
        edges = []
        # attach each node (in shuffled order) to a random ALREADY-PLACED node -> tree
        placed = [0]
        for v in order:
            u = rng.choice(placed)
            edges.append([u, v, rng.randint(0, 50)])
            placed.append(v)
        tree_pairs = {frozenset(e[:2]) for e in edges}
        pairs = [(u, v) for u in range(n) for v in range(u + 1, n)
                 if frozenset((u, v)) not in tree_pairs]
        rng.shuffle(pairs)
        for u, v in pairs[:rng.randint(0, n)]:
            edges.append([u, v, rng.randint(0, 50)])
        graphs.append({"n": n, "edges": edges})
    js2 = code + "\n;const gs=" + json.dumps(graphs) + \
        ";\nconsole.log(JSON.stringify(gs.map(g=>kruskal(g.n,g.edges))));"
    res = subprocess.run(["node", "-e", js2], capture_output=True, text=True, timeout=120)
    try:
        got2 = json.loads(res.stdout.strip())
    except Exception:
        print("FAIL: node random-run parse:", res.stderr[:300]); return 1
    bad = 0; disc = 0
    for g, a in zip(graphs, got2):
        k = kruskal_py(g["n"], g["edges"])
        if a != k: bad += 1                     # sealed == python-Kruskal on EVERY graph
        if connected(g["n"], g["edges"]):
            p = prim_mst(g["n"], g["edges"])
            if p is None or a != p: bad += 1    # Prim == both on connected graphs
        else:
            disc += 1                           # generator leak; counted, disclosed
    if bad == 0:
        print(f"random cross-check : 2000/2000 AGREE (sealed==python-Kruskal on all; ==python-Prim on the {2000 - disc} connected; {disc} disconnected generator leaks where Prim=null by contract)")
    else:
        print(f"random cross-check : {bad} MISMATCHES")
    fails += bad

    print(f"AUDITOR VERDICT    : {'PASS' if fails == 0 else 'FAIL'} ({fails} failures)")
    return 0 if fails == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
