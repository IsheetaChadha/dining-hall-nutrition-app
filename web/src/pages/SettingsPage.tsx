import { isApiError, validateSettings, type FieldErrors, type Settings } from '@dining/core';
import { useState, type FormEvent, type ReactNode } from 'react';
import { useSaveSettings, useSettings } from '../hooks/queries';
import styles from './SettingsPage.module.css';

interface BuildingRow {
  id: number;
  code: string;
  lat: string;
  lon: string;
}

interface Draft {
  protein: string;
  calories: string;
  meals: string;
  dayStart: string;
  dayEnd: string;
  keywords: string[];
  buildings: BuildingRow[];
}

let nextRowId = 0;

function toDraft(s: Settings): Draft {
  return {
    protein: String(s.protein_target_g),
    calories: String(s.calorie_limit),
    meals: String(s.meals_per_day),
    dayStart: s.day_start,
    dayEnd: s.day_end,
    keywords: [...s.restricted_keywords],
    buildings: Object.entries(s.building_coords).map(([code, [lat, lon]]) => ({
      id: nextRowId++, code, lat: String(lat), lon: String(lon),
    })),
  };
}

function toSettings(d: Draft): Settings {
  return {
    protein_target_g: Number(d.protein),
    calorie_limit: Number(d.calories),
    meals_per_day: Number(d.meals),
    day_start: d.dayStart,
    day_end: d.dayEnd,
    restricted_keywords: d.keywords,
    building_coords: Object.fromEntries(
      d.buildings.map((b) => [b.code.trim().toUpperCase(), [Number(b.lat), Number(b.lon)] as [number, number]]),
    ),
  };
}

export function SettingsPage() {
  const settings = useSettings();

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Settings</h1>
      <p className={styles.lede}>Your defaults for every plan. You can still adjust goals for a single plan.</p>
      {settings.isPending ? (
        <p role="status">Loading your settings…</p>
      ) : settings.isError ? (
        <p role="alert">{settings.error.message}</p>
      ) : (
        <SettingsForm initial={settings.data} />
      )}
    </div>
  );
}

function SettingsForm({ initial }: { initial: Settings }) {
  const [draft, setDraft] = useState(() => toDraft(initial));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [newKeyword, setNewKeyword] = useState('');
  const save = useSaveSettings();

  function edit(changes: Partial<Draft>) {
    setDraft((d) => ({ ...d, ...changes }));
    save.reset();
  }

  function addKeyword() {
    const keyword = newKeyword.trim().toLowerCase();
    if (keyword && !draft.keywords.includes(keyword)) edit({ keywords: [...draft.keywords, keyword] });
    setNewKeyword('');
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const settings = toSettings(draft);
    const found = validateSettings(settings);
    setErrors(found);
    if (Object.keys(found).length) return;
    save.mutate(settings, {
      onError: (error) => setErrors(isApiError(error) ? error.fields : {}),
    });
  }

  const summary = save.isError
    ? save.error.message
    : Object.keys(errors).length
      ? 'Fix the highlighted fields to save.'
      : null;

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <Section title="Daily goals" hint="Each meal's plate aims for an even share of these.">
        <div className={styles.row}>
          <NumberField label="Protein per day (g)" value={draft.protein} error={errors.protein_target_g}
            onChange={(protein) => edit({ protein })} />
          <NumberField label="Calories per day" value={draft.calories} error={errors.calorie_limit}
            onChange={(calories) => edit({ calories })} />
          <NumberField label="Meals per day" value={draft.meals} error={errors.meals_per_day}
            onChange={(meals) => edit({ meals })} />
        </div>
      </Section>

      <Section title="Day hours" hint="Free time is only looked for between these times.">
        <div className={styles.row}>
          <Field label="Day starts" error={errors.day_start}>
            {(id, describedBy) => (
              <input id={id} type="time" value={draft.dayStart} aria-describedby={describedBy}
                aria-invalid={!!errors.day_start} onChange={(e) => edit({ dayStart: e.target.value })} />
            )}
          </Field>
          <Field label="Day ends" error={errors.day_end}>
            {(id, describedBy) => (
              <input id={id} type="time" value={draft.dayEnd} aria-describedby={describedBy}
                aria-invalid={!!errors.day_end} onChange={(e) => edit({ dayEnd: e.target.value })} />
            )}
          </Field>
        </div>
      </Section>

      <Section title="Foods to avoid" hint="Any menu item whose name or ingredients mention one of these is left off your plate.">
        <ul className={styles.chips}>
          {draft.keywords.map((keyword) => (
            <li key={keyword} className={styles.chip}>
              {keyword}
              <button type="button" aria-label={`Remove ${keyword}`}
                onClick={() => edit({ keywords: draft.keywords.filter((k) => k !== keyword) })}>
                ×
              </button>
            </li>
          ))}
        </ul>
        <div className={styles.addRow}>
          <Field label="Add a food to avoid" error={errors.restricted_keywords}>
            {(id, describedBy) => (
              <input id={id} type="text" value={newKeyword} aria-describedby={describedBy} placeholder="e.g. lamb"
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addKeyword();
                  }
                }} />
            )}
          </Field>
          <button type="button" className={styles.secondary} onClick={addKeyword}>Add</button>
        </div>
      </Section>

      <Section title="Your buildings"
        hint="Buildings you have classes in, by the code in your calendar (WALC 2121 matches WALC). Picks near your next or last class rank higher.">
        {errors.building_coords && <p className={styles.error}>{errors.building_coords}</p>}
        <div className={styles.buildings}>
          {draft.buildings.map((b, index) => {
            const error = errors[`building_coords.${b.code.trim().toUpperCase()}`];
            const update = (changes: Partial<BuildingRow>) =>
              edit({ buildings: draft.buildings.map((row) => (row.id === b.id ? { ...row, ...changes } : row)) });
            return (
              <fieldset key={b.id} className={styles.building} aria-label={`Building ${b.code || index + 1}`}>
                <label className={styles.field}>
                  <span className={index === 0 ? styles.label : styles.srOnly}>Building code</span>
                  <input type="text" value={b.code} onChange={(e) => update({ code: e.target.value })} />
                </label>
                <label className={styles.field}>
                  <span className={index === 0 ? styles.label : styles.srOnly}>Latitude</span>
                  <input type="number" step="any" value={b.lat} aria-invalid={!!error} onChange={(e) => update({ lat: e.target.value })} />
                </label>
                <label className={styles.field}>
                  <span className={index === 0 ? styles.label : styles.srOnly}>Longitude</span>
                  <input type="number" step="any" value={b.lon} aria-invalid={!!error} onChange={(e) => update({ lon: e.target.value })} />
                </label>
                <button type="button" className={styles.remove} aria-label={`Remove ${b.code || 'building'}`}
                  onClick={() => edit({ buildings: draft.buildings.filter((row) => row.id !== b.id) })}>
                  Remove
                </button>
                {error && <p className={styles.error}>{error}</p>}
              </fieldset>
            );
          })}
        </div>
        <button type="button" className={styles.secondary}
          onClick={() => edit({ buildings: [...draft.buildings, { id: nextRowId++, code: '', lat: '', lon: '' }] })}>
          Add building
        </button>
      </Section>

      <div className={styles.actions}>
        <button type="submit" className={styles.primary} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save settings'}
        </button>
        {summary && <p role="alert" className={styles.error}>{summary}</p>}
        {save.isSuccess && <p role="status" className={styles.saved}>Settings saved.</p>}
      </div>
    </form>
  );
}

function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h2>{title}</h2>
        <p>{hint}</p>
      </div>
      <div className={styles.sectionBody}>{children}</div>
    </section>
  );
}

let nextFieldId = 0;

function Field({ label, error, children }: {
  label: string;
  error?: string;
  children: (id: string, describedBy?: string) => ReactNode;
}) {
  const [id] = useState(() => `field-${nextFieldId++}`);
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      {children(id, error ? `${id}-error` : undefined)}
      {error && <p id={`${id}-error`} className={styles.error}>{error}</p>}
    </div>
  );
}

function NumberField({ label, value, error, onChange }: {
  label: string;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label} error={error}>
      {(id, describedBy) => (
        <input id={id} type="number" min={0} step="any" value={value} aria-describedby={describedBy}
          aria-invalid={!!error} onChange={(e) => onChange(e.target.value)} />
      )}
    </Field>
  );
}
