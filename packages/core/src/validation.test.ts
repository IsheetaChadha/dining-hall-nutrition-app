import { describe, expect, it } from 'vitest';
import type { Settings } from './types';
import { validateSettings } from './validation';

const valid: Settings = {
  protein_target_g: 100,
  calorie_limit: 1800,
  meals_per_day: 3,
  day_start: '07:00',
  day_end: '21:00',
  restricted_keywords: ['beef'],
  building_coords: { WALC: [40.4274, -86.9132] },
};

describe('validateSettings', () => {
  it('accepts valid settings', () => {
    expect(validateSettings(valid)).toEqual({});
  });

  it('flags non-positive goals and an out-of-range meal count', () => {
    expect(validateSettings({ ...valid, protein_target_g: 0, calorie_limit: -1, meals_per_day: 7 })).toEqual({
      protein_target_g: 'Must be more than 0.',
      calorie_limit: 'Must be more than 0.',
      meals_per_day: 'Must be between 1 and 6.',
    });
  });

  it('flags a day that ends before it starts', () => {
    expect(validateSettings({ ...valid, day_start: '20:00', day_end: '08:00' })).toEqual({
      day_end: 'Day end must be after day start.',
    });
  });

  it('flags blank keywords and out-of-range coordinates by building', () => {
    expect(
      validateSettings({ ...valid, restricted_keywords: ['beef', ' '], building_coords: { WALC: [91, 0], '': [40, -86] } }),
    ).toEqual({
      restricted_keywords: "Keywords can't be blank.",
      'building_coords.WALC': 'Latitude must be within ±90 and longitude within ±180.',
      building_coords: "Building codes can't be blank.",
    });
  });
});
