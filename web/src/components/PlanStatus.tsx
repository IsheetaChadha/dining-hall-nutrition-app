import type { ApiError } from '@dining/core';
import { useState } from 'react';
import styles from './PlanStatus.module.css';

export function PlanLoading() {
  return (
    <div className={styles.loading} role="status">
      <span className={styles.srOnly}>Finding the best meals for your free time…</span>
      <div className={styles.skeletonRail} aria-hidden="true" />
      <div className={styles.skeletonPick} aria-hidden="true" />
      <p className={styles.slow} aria-hidden="true">Checking menus across dining halls. This can take a few seconds.</p>
    </div>
  );
}

export function PlanEmpty({ notice }: { notice?: string | null }) {
  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>{notice ?? 'None of your free time lines up with a dining hall meal.'}</h2>
      <p>Pick another day or meal above, or widen your day hours in Settings.</p>
    </div>
  );
}

export function CalendarSetup() {
  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Connect your calendar</h2>
      <p>The planner reads your calendar to find free time between classes. To connect it:</p>
      <ol className={styles.steps}>
        <li>In Google Calendar on the web, open Settings, choose your calendar, then Integrate calendar.</li>
        <li>Copy the Secret address in iCal format.</li>
        <li>
          Save it to <code>credentials/calendar_url.txt</code> in the planner folder, then reload this page.
        </li>
      </ol>
    </div>
  );
}

export function PlanError({ error, onRetry }: { error: ApiError | Error; onRetry: () => void }) {
  return (
    <div className={styles.panel} role="alert">
      <h2 className={styles.title}>{error.message}</h2>
      <button type="button" className={styles.retry} onClick={onRetry}>Try again</button>
    </div>
  );
}

export function Warnings({ warnings }: { warnings: string[] }) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  const key = warnings.join('\n');
  if (!warnings.length || dismissed === key) return null;
  return (
    <div className={styles.warnings}>
      <ul>
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      <button type="button" className={styles.dismiss} onClick={() => setDismissed(key)}>
        Dismiss
      </button>
    </div>
  );
}
