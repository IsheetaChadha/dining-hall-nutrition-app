import { formatWindow, type Recommendation, type Window } from '@dining/core';
import styles from './DayRail.module.css';

interface Props {
  windows: Window[];
  recommendations: Recommendation[];
  dayStart: string; // "HH:MM"
  dayEnd: string;
  now?: Date; // draws a "now" line when planning today
}

const clockMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(':').map(Number) as [number, number];
  return h * 60 + m;
};
const localMinutes = (when: string | Date) => {
  const d = new Date(when);
  return d.getHours() * 60 + d.getMinutes();
};
const hourLabel = (hour: number) => `${((hour + 11) % 12) + 1}${hour < 12 ? 'a' : 'p'}`;

/** Your free windows across the day, with the ranked picks that fall inside each. */
export function DayRail({ windows, recommendations, dayStart, dayEnd, now }: Props) {
  const start = clockMinutes(dayStart);
  const end = Math.max(clockMinutes(dayEnd), start + 60);
  const pct = (minutes: number) => `${((Math.min(Math.max(minutes, start), end) - start) / (end - start)) * 100}%`;

  const ranksByWindow = new Map<string, number[]>();
  for (const rec of recommendations) {
    const key = `${rec.window.start}|${rec.window.end}`;
    ranksByWindow.set(key, [...(ranksByWindow.get(key) ?? []), rec.rank]);
  }

  const hours: number[] = [];
  for (let h = Math.ceil(start / 60); h * 60 <= end; h += 1) hours.push(h);

  return (
    <figure className={styles.rail}>
      <figcaption className={styles.caption}>Your free time</figcaption>
      <div className={styles.track}>
        {hours.map((h, i) => (
          <span
            key={h}
            className={`${styles.tick} ${i === 0 ? styles.first : ''} ${i === hours.length - 1 ? styles.last : ''}`}
            style={{ left: pct(h * 60) }}
            aria-hidden="true"
          >
            <span className={styles.tickLabel}>{hourLabel(h)}</span>
          </span>
        ))}
        <ol className={styles.windows}>
          {windows.map((w) => {
            const ranks = ranksByWindow.get(`${w.start}|${w.end}`) ?? [];
            const from = localMinutes(w.start);
            const to = localMinutes(w.end);
            return (
              <li
                key={w.start}
                className={`${styles.window} ${ranks.includes(1) ? styles.best : ''}`}
                style={{ left: pct(from), width: `calc(${pct(to)} - ${pct(from)})` }}
              >
                <span className={styles.srOnly}>
                  Free {formatWindow(w.start, w.end)}
                  {ranks.length ? `, picks ${ranks.join(', ')}` : ', no picks'}
                </span>
                <span className={styles.ranks} aria-hidden="true">
                  {ranks.slice(0, 2).map((rank) => (
                    <span key={rank} className={styles.rank}>{rank}</span>
                  ))}
                  {ranks.length > 2 && <span className={styles.more}>+{ranks.length - 2}</span>}
                </span>
              </li>
            );
          })}
        </ol>
        {now && localMinutes(now) > start && localMinutes(now) < end && (
          <span className={styles.now} style={{ left: pct(localMinutes(now)) }}>
            <span className={styles.srOnly}>Now</span>
          </span>
        )}
      </div>
    </figure>
  );
}
