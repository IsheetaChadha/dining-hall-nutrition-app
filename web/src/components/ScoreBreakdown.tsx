import { scoreToPercent, type Scores } from '@dining/core';
import styles from './ScoreBreakdown.module.css';

const PARTS = [
  { key: 'nutrition', label: 'Nutrition' },
  { key: 'time', label: 'Time' },
  { key: 'proximity', label: 'Proximity' },
] as const;

export function ScoreBreakdown({ scores }: { scores: Scores }) {
  return (
    <dl className={styles.list}>
      {PARTS.map(({ key, label }) => {
        const value = scores[key];
        return (
          <div key={key} className={styles.part}>
            <dt>{label}</dt>
            {value == null ? (
              <dd className={styles.unknown}>Location unknown</dd>
            ) : (
              <dd>
                <span className={styles.bar} aria-hidden="true">
                  <span style={{ width: `${scoreToPercent(value)}%` }} />
                </span>
                {scoreToPercent(value)}%
              </dd>
            )}
          </div>
        );
      })}
    </dl>
  );
}
