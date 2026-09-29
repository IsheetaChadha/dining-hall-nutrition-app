import { goalDelta, plateTotals, type Goal, type PlateItem } from '@dining/core';
import styles from './PlateTable.module.css';

const n = (value: number) => Math.round(value).toLocaleString();

function deltaText(delta: number, unit: string, over: string, under: string) {
  const amount = `${n(Math.abs(delta))}${unit}`;
  return delta >= 0 ? `${amount} ${over}` : `${amount} ${under}`;
}

export function PlateTable({ plate, goal }: { plate: PlateItem[]; goal: Goal }) {
  const totals = plateTotals(plate);
  const delta = goalDelta(totals, goal);

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption className={styles.caption}>Suggested plate</caption>
        <thead>
          <tr>
            <th scope="col">Item</th>
            <th scope="col" className={styles.num}>Calories</th>
            <th scope="col" className={styles.num}>Protein</th>
            <th scope="col" className={`${styles.num} ${styles.minor}`}>Fat</th>
            <th scope="col" className={`${styles.num} ${styles.minor}`}>Carbs</th>
          </tr>
        </thead>
        <tbody>
          {plate.map((item) => (
            <tr key={item.id}>
              <th scope="row">
                <span className={styles.name}>{item.name}</span>
                <span className={styles.station}>{item.station}</span>
              </th>
              {item.nutrition ? (
                <>
                  <td className={styles.num}>{n(item.nutrition.calories)}</td>
                  <td className={`${styles.num} ${styles.protein}`}>{n(item.nutrition.protein_g)} g</td>
                  <td className={`${styles.num} ${styles.minor}`}>{n(item.nutrition.fat_g)} g</td>
                  <td className={`${styles.num} ${styles.minor}`}>{n(item.nutrition.carbs_g)} g</td>
                </>
              ) : (
                <td colSpan={4} className={styles.missing}>No nutrition info</td>
              )}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Plate total</th>
            <td className={styles.num}>{n(totals.calories)}</td>
            <td className={`${styles.num} ${styles.protein}`}>{n(totals.protein_g)} g</td>
            <td className={`${styles.num} ${styles.minor}`}>{n(totals.fat_g)} g</td>
            <td className={`${styles.num} ${styles.minor}`}>{n(totals.carbs_g)} g</td>
          </tr>
        </tfoot>
      </table>
      <p className={styles.goal}>
        Meal goal is {n(goal.protein_g)} g protein within {n(goal.calories)} calories. This plate is{' '}
        {deltaText(delta.protein_g, ' g', 'over on protein', 'short on protein')} and{' '}
        {deltaText(delta.calories, '', 'calories over', 'calories under')}.
      </p>
    </div>
  );
}
