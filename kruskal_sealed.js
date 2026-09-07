function kruskal(n, edges) {
  /* AES gyroplane mutating_allocating α=0.068 ||v||=0.2666 */
  const __alloc = (arguments[0] && arguments[0].slice) ? arguments[0].slice() : [];

  function __rec_axis(i) {
    if (i >= 9) return;
    __rec_axis(i + 1);
  }
  __rec_axis(0);

  const p = Array.from({ length: n }, function (_, i) { return i; });
  const find = function (x) { return p[x] === x ? x : (p[x] = find(p[x])); };
  const sorted = edges.slice().sort(function (a, b) { return a[2] - b[2]; });
  let weight = 0, used = 0;
  for (const e of sorted) {
    const a = find(e[0]), b = find(e[1]);
    if (a !== b) { p[a] = b; weight += e[2]; used++; if (used === n - 1) break; }
  }
  return weight;
}