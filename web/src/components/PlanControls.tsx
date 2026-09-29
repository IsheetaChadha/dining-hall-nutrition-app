import { toISODate, type RecommendationRequest, type Settings } from '@dining/core';
import { useState, type FormEvent } from 'react';
import type { GoalOverrides } from '../hooks/usePlanParams';
import styles from './PlanControls.module.css';

interface Props {
  request: RecommendationRequest;
  meals: string[];
  settings?: Settings;
  onDate: (date: string | undefined) => void;
  onMeal: (meal: string | undefined) => void;
  onGoals: (goals: GoalOverrides) => void;
  onNow: () => void;
}

export function PlanControls({ request, meals, settings, onDate, onMeal, onGoals, onNow }: Props) {
  const today = toISODate(new Date());
  const isNow = !request.date && !request.meal;
  const goals = {
    protein: request.protein ?? settings?.protein_target_g,
    calories: request.calories ?? settings?.calorie_limit,
    meals: request.meals ?? settings?.meals_per_day,
  };

  return (
    <div className={styles.controls}>
      <div className={styles.when}>
        <button type="button" className={styles.now} aria-pressed={isNow} onClick={onNow}>
          Now
        </button>
        <label className={styles.date}>
          <span className={styles.label}>Date</span>
          <input
            type="date"
            value={request.date ?? today}
            onChange={(e) => onDate(e.target.value && e.target.value !== today ? e.target.value : undefined)}
          />
        </label>
      </div>

      <fieldset className={styles.meals}>
        <legend className={styles.label}>Meal</legend>
        {['', ...meals].map((meal) => (
          <label key={meal || 'any'} className={styles.chip}>
            <input
              type="radio"
              name="meal"
              value={meal}
              checked={(request.meal ?? '') === meal}
              onChange={() => onMeal(meal || undefined)}
            />
            <span>{meal || 'Any meal'}</span>
          </label>
        ))}
      </fieldset>

      {settings && (
        <GoalsEditor key={JSON.stringify(goals)} initial={goals as Required<GoalOverrides>} onApply={onGoals} />
      )}
    </div>
  );
}

function GoalsEditor({ initial, onApply }: { initial: Required<GoalOverrides>; onApply: (g: GoalOverrides) => void }) {
  const [draft, setDraft] = useState({
    protein: String(initial.protein),
    calories: String(initial.calories),
    meals: String(initial.meals),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    onApply({ protein: Number(draft.protein), calories: Number(draft.calories), meals: Number(draft.meals) });
  }

  const field = (key: keyof typeof draft, label: string, props: { min: number; max?: number; step: number }) => (
    <label className={styles.goalField}>
      <span className={styles.label}>{label}</span>
      <input
        type="number"
        required
        {...props}
        value={draft[key]}
        onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
      />
    </label>
  );

  return (
    <details className={styles.goals}>
      <summary>
        Goals: {initial.protein.toLocaleString()} g protein, {initial.calories.toLocaleString()} cal,{' '}
        {initial.meals} {initial.meals === 1 ? 'meal' : 'meals'}
      </summary>
      <form className={styles.goalForm} onSubmit={submit}>
        {field('protein', 'Protein per day (g)', { min: 1, step: 1 })}
        {field('calories', 'Calories per day', { min: 1, step: 1 })}
        {field('meals', 'Meals per day', { min: 1, max: 6, step: 1 })}
        <button type="submit" className={styles.apply}>Update picks</button>
      </form>
      <p className={styles.hint}>Applies to this plan only. Change your defaults in Settings.</p>
    </details>
  );
}
