import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { apiError, fakeApi, PLAN, renderWithApp } from '../test/render';
import { PlanPage } from './PlanPage';

describe('PlanPage', () => {
  it('plans from now by default and shows the top pick with its plate', async () => {
    const { api } = renderWithApp(<PlanPage />);

    const top = await screen.findByRole('region', { name: 'Top pick' });
    expect(within(top).getByRole('heading', { name: 'Lunch at Wiley' })).toBeInTheDocument();
    expect(within(top).getByText('Grilled Chicken')).toBeInTheDocument();
    expect(within(top).getByText('Great fit, 86%')).toBeInTheDocument();
    expect(within(top).getByText('Location unknown')).toBeInTheDocument();
    expect(api.getRecommendations).toHaveBeenCalledWith({});
  });

  it('lists the other options and opens one to show its plate', async () => {
    renderWithApp(<PlanPage />);

    const others = await screen.findByRole('region', { name: 'Other options' });
    const row = within(others).getByRole('button', { name: /Dinner at Ford/ });
    expect(row).toHaveAttribute('aria-expanded', 'false');

    await userEvent.click(row);

    expect(row).toHaveAttribute('aria-expanded', 'true');
    expect(within(others).getByText('Turkey Burger')).toBeInTheDocument();
  });

  it('asks for a single meal when its chip is chosen', async () => {
    const { api } = renderWithApp(<PlanPage />);

    await userEvent.click(await screen.findByRole('radio', { name: 'Dinner' }));

    expect(api.getRecommendations).toHaveBeenLastCalledWith({ meal: 'Dinner' });
  });

  it('plans a chosen date from the URL', async () => {
    const { api } = renderWithApp(<PlanPage />, { route: '/?date=2026-10-02' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Where to eat on Fri, Oct 2' })).toBeInTheDocument();
    expect(api.getRecommendations).toHaveBeenCalledWith({ date: '2026-10-02' });
    expect(api.getMeals).toHaveBeenCalledWith('2026-10-02');
  });

  it('goes back to planning from now', async () => {
    const { api } = renderWithApp(<PlanPage />, { route: '/?date=2026-10-02&meal=Lunch' });
    await screen.findByRole('region', { name: 'Top pick' });

    await userEvent.click(screen.getByRole('button', { name: 'Now' }));

    expect(api.getRecommendations).toHaveBeenLastCalledWith({});
    expect(screen.getByRole('heading', { level: 1, name: 'Where to eat today' })).toBeInTheDocument();
  });

  it('applies goal changes for this plan only', async () => {
    const { api } = renderWithApp(<PlanPage />);
    await userEvent.click(await screen.findByText(/^Goals:/));

    const protein = await screen.findByLabelText('Protein per day (g)');
    await userEvent.clear(protein);
    await userEvent.type(protein, '130');
    await userEvent.click(screen.getByRole('button', { name: 'Update picks' }));

    expect(api.getRecommendations).toHaveBeenLastCalledWith({ protein: 130, calories: 1800, meals: 3 });
    expect(api.updateSettings).not.toHaveBeenCalled();
  });

  it('explains an empty plan with the server notice', async () => {
    const api = fakeApi({
      getRecommendations: vi.fn(async () => ({ ...PLAN, recommendations: [], notice: 'Lunch has ended for today.' })),
    });
    renderWithApp(<PlanPage />, { api });

    expect(await screen.findByText('Lunch has ended for today.')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Top pick' })).not.toBeInTheDocument();
  });

  it('walks through calendar setup when no calendar is connected', async () => {
    const api = fakeApi({
      getRecommendations: vi.fn(async () => {
        throw apiError(409, 'calendar_not_configured', 'No calendar is connected.');
      }),
    });
    renderWithApp(<PlanPage />, { api });

    expect(await screen.findByRole('heading', { name: 'Connect your calendar' })).toBeInTheDocument();
    expect(screen.getByText(/credentials\/calendar_url\.txt/)).toBeInTheDocument();
  });

  it('shows what went wrong and retries', async () => {
    const getRecommendations = vi
      .fn()
      .mockRejectedValueOnce(apiError(502, 'upstream_unavailable', "Couldn't reach Purdue Dining. Try again in a moment."))
      .mockResolvedValue(structuredClone(PLAN));
    renderWithApp(<PlanPage />, { api: fakeApi({ getRecommendations }) });

    expect(await screen.findByText("Couldn't reach Purdue Dining. Try again in a moment.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('region', { name: 'Top pick' })).toBeInTheDocument();
  });

  it('flags halls that were skipped', async () => {
    const api = fakeApi({
      getRecommendations: vi.fn(async () => ({ ...PLAN, warnings: ["Couldn't load the Ford menu, so it was skipped."] })),
    });
    renderWithApp(<PlanPage />, { api });

    expect(await screen.findByText("Couldn't load the Ford menu, so it was skipped.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));

    expect(screen.queryByText("Couldn't load the Ford menu, so it was skipped.")).not.toBeInTheDocument();
  });
});
