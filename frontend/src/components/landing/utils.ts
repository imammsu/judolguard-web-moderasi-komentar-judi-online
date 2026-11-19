/** Inisial untuk avatar: "slotgacor_id" -> "S", "Nama Channel" -> "NC". */
export function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  const first = (parts[0] || '')[0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

/** Hue dari string, untuk warna avatar. */
export function hueOf(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
  return h;
}

/** 1240 -> "1.240" (format Indonesia). */
export function fmt(n: number, decimals = 0) {
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Skor 0..1 -> "98%" ("<1%" bila hampir nol). */
export function scoreText(s: number) {
  return s < 0.01 ? '<1%' : `${Math.round(s * 100)}%`;
}
