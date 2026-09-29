import { formatWindow, scoreToPercent, type Goal, type Recommendation } from '@dining/core';
import { useState } from 'react';
import styles from './OptionList.module.css';
import { PlateTable } from './PlateTable';
import { ScoreBreakdown } from './ScoreBreakdown';

export function OptionList({ options, goal }: { options: Recommendation[]; goal: Goal }) {
  const [open, setOpen] = useState<string | null>(null);

  return (
    <section className={styles.section} aria-labelledby="other-options-title">
      <h2 id="other-options-title" className={styles.title}>Other options</h2>
      <ol className={styles.list}>
        {options.map((option) => {
          const id = `${option.dining_hall}-${option.meal}`;
          const expanded = open === id;
          return (
            <li key={id} className={styles.item}>
              <button
                type="button"
                className={styles.row}
                aria-expanded={expanded}
                aria-controls={`${id}-details`}
                onClick={() => setOpen(expanded ? null : id)}
              >
                <span className={styles.rank}>{option.rank}</span>
                <span className={styles.name}>
                  {option.meal} at {option.dining_hall}
                </span>
                <span className={styles.when}>{formatWindow(option.window.start, option.window.end)}</span>
                <span className={styles.score}>{scoreToPercent(option.scores.total)}%</span>
                <span className={styles.chevron} aria-hidden="true" />
              </button>
              {expanded && (
                <div id={`${id}-details`} className={styles.details}>
                  <ScoreBreakdown scores={option.scores} />
                  <PlateTable plate={option.plate} goal={goal} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
