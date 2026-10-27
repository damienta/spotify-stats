// Turn the API's sparse minutes lists into a full set of bars: every hour of today, every day
// of this week or month, every month of this year. Uses the browser's clock, which for now is
// the same as the stats' (Europe/London).

import type { ChartPoint } from '@/components/MinutesChart'

import type { Period } from './types'

export type PeriodName = 'today' | 'this_week' | 'this_month' | 'this_year'

export const GRAIN_STAT: Record<PeriodName, string> = {
  today: 'minutes_by_hour',
  this_week: 'minutes_by_day',
  this_month: 'minutes_by_day',
  this_year: 'minutes_by_month',
}

const pad = (n: number) => String(n).padStart(2, '0')
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function fillPeriod(period: PeriodName, data: Period[], now = new Date()): ChartPoint[] {
  // Hours are matched on "YYYY-MM-DDTHH", days and months on "YYYY-MM-DD".
  const minutes = new Map<string, number>()
  for (const p of data) minutes.set(p.start.slice(0, period === 'today' ? 13 : 10), p.minutes)
  const at = (key: string) => minutes.get(key) ?? 0

  if (period === 'today') {
    return Array.from({ length: 24 }, (_, h) => ({
      label: `${pad(h)}:00`,
      minutes: at(`${ymd(now)}T${pad(h)}`),
      highlight: h === now.getHours(),
    }))
  }
  if (period === 'this_week') {
    const sinceMonday = (now.getDay() + 6) % 7
    return WEEKDAYS.map((label, i) => {
      const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() - sinceMonday + i)
      return { label, minutes: at(ymd(day)), highlight: i === sinceMonday }
    })
  }
  if (period === 'this_month') {
    const days = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
    return Array.from({ length: days }, (_, i) => ({
      label: String(i + 1),
      minutes: at(ymd(new Date(now.getFullYear(), now.getMonth(), i + 1))),
      highlight: i + 1 === now.getDate(),
    }))
  }
  return MONTHS.map((label, m) => ({
    label,
    minutes: at(`${now.getFullYear()}-${pad(m + 1)}-01`),
    highlight: m === now.getMonth(),
  }))
}
