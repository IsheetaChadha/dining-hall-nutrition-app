import { NavLink, Outlet } from 'react-router-dom';
import styles from './AppShell.module.css';

export function AppShell() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <p className={styles.brand}>
          <span className={styles.mark} aria-hidden="true" />
          Dining Planner
        </p>
        <nav aria-label="Main">
          <ul className={styles.nav}>
            <li><NavLink to="/" end className={({ isActive }) => (isActive ? styles.active : undefined)}>Plan</NavLink></li>
            <li><NavLink to="/settings" className={({ isActive }) => (isActive ? styles.active : undefined)}>Settings</NavLink></li>
          </ul>
        </nav>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
