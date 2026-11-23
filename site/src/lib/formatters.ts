export function formatYen(value: number): string {
  return `${Math.round(value).toLocaleString("ja-JP")}円`;
}

export function formatSignedYen(value: number): string {
  const rounded = Math.round(value);
  if (rounded > 0) return `+${rounded.toLocaleString("ja-JP")}円`;
  if (rounded < 0) return `▲${Math.abs(rounded).toLocaleString("ja-JP")}円`;
  return "±0円";
}

export function formatManYen(value: number): string {
  const man = Math.round(value / 10000);
  return `${man.toLocaleString("ja-JP")}万円`;
}

export function formatManFloat(value: number, digits = 1): string {
  return `${value.toFixed(digits)}万円`;
}

export function formatDiffMan(value: number, unit = "万円/坪"): string {
  if (value > 0) return `+${value.toFixed(2)}${unit}`;
  if (value < 0) return `${value.toFixed(2)}${unit}`;
  return `±0.00${unit}`;
}

export function structureLabel(structure: string): string {
  switch (structure) {
    case "steel":
      return "鉄骨造（S造）";
    case "rc":
      return "RC造（鉄筋コンクリート）";
    case "grave":
      return "墓石・墓地（改葬）";
    default:
      return "木造";
  }
}

export function roadConditionLabel(road: string): string {
  switch (road) {
    case "narrow":
      return "狭小道路（重機制限・手壊し割増）";
    case "slope":
      return "傾斜地・階段上（小運搬割増）";
    default:
      return "標準道路（4m以上・重機進入可）";
  }
}

export function residualLevelLabel(level: string): string {
  switch (level) {
    case "minimal":
      return "ほぼ片付いている（少量）";
    case "heavy":
      return "残置物多め（全室家財そのまま）";
    default:
      return "標準的な家財残り";
  }
}
