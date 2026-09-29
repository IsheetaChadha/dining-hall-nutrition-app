import { formatWindow, scoreLabel, scoreToPercent, type Goal, type Recommendation } from '@dining/core';
import { PlateTable } from './PlateTable';
import { ScoreBreakdown } from './ScoreBreakdown';
import styles from './TopPick.module.css';

export function TopPick({ pick, goal }: { pick: Recommendation; goal: Goal }) {
  return (
    <section className={styles.pick} aria-label="Top pick">
      <div className={styles.head}>
        <div>
          <h2 className={styles.title}>
            {pick.meal} at {pick.dining_hall}
          </h2>
          <p className={styles.when}>You're free {formatWindow(pick.window.start, pick.window.end)}</p>
        </div>
        <p className={styles.score}>
          {scoreLabel(pick.scores.total)}, {scoreToPercent(pick.scores.total)}%
        </p>
      </div>
      <ScoreBreakdown scores={pick.scores} />
      <PlateTable plate={pick.plate} goal={goal} />
    </section>
  );
}
