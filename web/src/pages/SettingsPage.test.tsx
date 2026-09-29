import { fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { apiError, fakeApi, renderWithApp, SETTINGS } from '../test/render';
import { SettingsPage } from './SettingsPage';

async function renderLoaded(api = fakeApi()) {
  renderWithApp(<SettingsPage />, { api, route: '/settings' });
  await screen.findByDisplayValue('1800');
  return api;
}

describe('SettingsPage', () => {
  it('fills the form with the saved settings', async () => {
    await renderLoaded();

    expect(screen.getByLabelText('Protein per day (g)')).toHaveValue(100);
    expect(screen.getByLabelText('Meals per day')).toHaveValue(3);
    expect(screen.getByLabelText('Day starts')).toHaveValue('07:00');
    expect(screen.getByRole('button', { name: 'Remove beef' })).toBeInTheDocument();
    expect(screen.getByLabelText('Building code')).toHaveValue('WALC');
  });

  it('saves edited goals and confirms', async () => {
    const api = await renderLoaded();

    const protein = screen.getByLabelText('Protein per day (g)');
    await userEvent.clear(protein);
    await userEvent.type(protein, '130');
    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(api.updateSettings).toHaveBeenCalledWith({ ...SETTINGS, protein_target_g: 130 });
    expect(await screen.findByText('Settings saved.')).toBeInTheDocument();
  });

  it('adds and removes dietary keywords', async () => {
    const api = await renderLoaded();

    await userEvent.type(screen.getByLabelText('Add a food to avoid'), 'Lamb{Enter}');
    await userEvent.click(screen.getByRole('button', { name: 'Remove beef' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(api.updateSettings).toHaveBeenCalledWith(expect.objectContaining({ restricted_keywords: ['pork', 'lamb'] }));
  });

  it('adds a building', async () => {
    const api = await renderLoaded();

    await userEvent.click(screen.getByRole('button', { name: 'Add building' }));
    const rows = screen.getAllByRole('group', { name: /^Building/ });
    const added = rows[rows.length - 1]!;
    await userEvent.type(within(added).getByLabelText('Building code'), 'lwsn');
    await userEvent.type(within(added).getByLabelText('Latitude'), '40.4278');
    await userEvent.type(within(added).getByLabelText('Longitude'), '-86.917');
    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(api.updateSettings).toHaveBeenCalledWith(
      expect.objectContaining({ building_coords: { WALC: [40.4274, -86.9132], LWSN: [40.4278, -86.917] } }),
    );
  });

  it('points out invalid values without saving', async () => {
    const api = await renderLoaded();

    fireEvent.change(screen.getByLabelText('Day ends'), { target: { value: '06:00' } });
    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(await screen.findByText('Day end must be after day start.')).toBeInTheDocument();
    expect(api.updateSettings).not.toHaveBeenCalled();
  });

  it('shows the server field errors next to their fields', async () => {
    const api = fakeApi({
      updateSettings: vi.fn(async () => {
        throw apiError(422, 'invalid_settings', "Some values aren't valid.", {
          'building_coords.WALC': 'Input should be less than or equal to 90',
        });
      }),
    });
    await renderLoaded(api);

    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(await screen.findByText('Input should be less than or equal to 90')).toBeInTheDocument();
    expect(screen.getByText("Some values aren't valid.")).toBeInTheDocument();
  });
});
