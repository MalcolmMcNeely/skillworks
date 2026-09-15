// WCAG 2's relative luminance, which its 4.5:1 and 3:1 thresholds are measured in.
function luminance(hex: string): number {
  const [red, green, blue] = [1, 3, 5].map((start) => {
    const channel = Number.parseInt(hex.slice(start, start + 2), 16) / 255;

    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

export function contrast(one: string, other: string): number {
  const [lighter, darker] = [luminance(one), luminance(other)].toSorted((a, b) => b - a);

  return (lighter + 0.05) / (darker + 0.05);
}
