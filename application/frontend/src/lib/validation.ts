export function isAggregateSeason(value: string) {
  return value.trim().toLocaleLowerCase() === "total";
}

export type CropNamesResult =
  | { valid: true; crops: string[] }
  | { valid: false; reason: "too-few" | "duplicate" };

export function parseCropNames(value: string): CropNamesResult {
  const crops = value
    .split(",")
    .map((crop) => crop.trim())
    .filter(Boolean);
  if (crops.length < 2) return { valid: false, reason: "too-few" };
  if (new Set(crops).size !== crops.length) {
    return { valid: false, reason: "duplicate" };
  }
  return { valid: true, crops };
}
