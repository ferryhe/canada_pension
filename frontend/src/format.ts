export function money(value: number): string {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0
  }).format(value);
}

export function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
