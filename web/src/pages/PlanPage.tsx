import { dayLabel, isApiError, toISODate } from '@dining/core';
import { DayRail } from '../components/DayRail';
import { OptionList } from '../components/OptionList';
import { PlanControls } from '../components/PlanControls';
import { CalendarSetup, PlanEmpty, PlanError, PlanLoading, Warnings } from '../components/PlanStatus';
import { TopPick } from '../components/TopPick';
import { useMeals, useRecommendations, useSettings } from '../hooks/queries';
import { usePlanParams } from '../hooks/usePlanParams';
import styles from './PlanPage.module.css';

function headingFor(date: string | undefined) {
  const label = dayLabel(date ?? toISODate(new Date()));
  return label === 'Today' || label === 'Tomorrow' ? `Where to eat ${label.toLowerCase()}` : `Where to eat on ${label}`;
}

export function PlanPage() {
  const { request, setDate, setMeal, setGoals, resetToNow } = usePlanParams();
  const settings = useSettings();
  const meals = useMeals(request.date ?? undefined);
  const plan = useRecommendations(request);

  const [top, ...others] = plan.data?.recommendations ?? [];
  const planningToday = !request.date || request.date === toISODate(new Date());

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{headingFor(request.date ?? undefined)}</h1>
        <PlanControls
          request={request}
          meals={meals.data?.meals ?? []}
          settings={settings.data}
          onDate={setDate}
          onMeal={setMeal}
          onGoals={setGoals}
          onNow={resetToNow}
        />
      </header>

      {plan.isPending ? (
        <PlanLoading />
      ) : plan.isError ? (
        isApiError(plan.error, 'calendar_not_configured') ? (
          <CalendarSetup />
        ) : (
          <PlanError error={plan.error} onRetry={() => void plan.refetch()} />
        )
      ) : (
        <>
          <Warnings warnings={plan.data.warnings} />
          <DayRail
            windows={plan.data.windows}
            recommendations={plan.data.recommendations}
            dayStart={settings.data?.day_start ?? '07:00'}
            dayEnd={settings.data?.day_end ?? '21:00'}
            now={planningToday ? new Date() : undefined}
          />
          {top ? (
            <>
              <TopPick pick={top} goal={plan.data.goal_per_meal} />
              {others.length > 0 && <OptionList options={others} goal={plan.data.goal_per_meal} />}
            </>
          ) : (
            <PlanEmpty notice={plan.data.notice} />
          )}
        </>
      )}
    </div>
  );
}
