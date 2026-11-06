/**
 * 源图标兜底：很多源没有 /logo/<key>.png（尤其 newsnow 独有的源），
 * 直接用 <img> 会出现碎图 / n-avatar 的 fallback 错误图标。
 * 这里统一用「文字头像」兜底——首字 + 由名称派生的稳定底色，零图片资源。
 */
const PALETTE = [
  "#5B8FF9", "#61DDAA", "#65789B", "#F6BD16", "#7262FD",
  "#78D3F8", "#9661BC", "#F6903D", "#008685", "#F08BB4",
];

/** 由源名派生一个稳定的颜色（同一源每次颜色一致） */
export function avatarStyle(label = "") {
  const s = String(label);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.codePointAt(i)) % 9973;
  return {
    background: PALETTE[h % PALETTE.length],
    color: "#fff",
    fontSize: "1.05em",
    fontWeight: "500",
  };
}

/** 中文取首字，英文/数字取首字符大写 */
export function initialOf(label = "") {
  const s = String(label).trim();
  if (!s) return "?";
  const c = s[0];
  return /[\u4e00-\u9fa5]/.test(c) ? c : c.toUpperCase();
}
