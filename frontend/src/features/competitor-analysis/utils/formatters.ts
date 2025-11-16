export const formatLabel = (value: string): string =>
  value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, letter => letter.toUpperCase())

export const formatPriceDisplay = (
  amount: number | null | undefined,
  currency?: string | null
): string => {
  if (amount === null || amount === undefined) {
    return currency ?? 'n/a'
  }

  const formatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2
  })

  const formatted = formatter.format(amount)
  return currency ? `${currency} ${formatted}` : formatted
}












