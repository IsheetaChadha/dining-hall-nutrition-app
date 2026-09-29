import type { Settings } from './types';

export type FieldErrors = Record<string, string>;

/** Client-side mirror of the API's settings rules; keys match the API's `fields` keys. */
export function validateSettings(settings: Settings): FieldErrors {
  const errors: FieldErrors = {};

  if (!(settings.protein_target_g > 0)) errors.protein_target_g = 'Must be more than 0.';
  if (!(settings.calorie_limit > 0)) errors.calorie_limit = 'Must be more than 0.';
  if (!Number.isInteger(settings.meals_per_day) || settings.meals_per_day < 1 || settings.meals_per_day > 6) {
    errors.meals_per_day = 'Must be between 1 and 6.';
  }

  const clock = /^([01]\d|2[0-3]):[0-5]\d$/;
  if (!clock.test(settings.day_start)) errors.day_start = 'Use a 24-hour HH:MM time.';
  if (!clock.test(settings.day_end)) errors.day_end = 'Use a 24-hour HH:MM time.';
  else if (clock.test(settings.day_start) && settings.day_end <= settings.day_start) {
    errors.day_end = 'Day end must be after day start.';
  }

  if (settings.restricted_keywords.some((k) => !k.trim())) {
    errors.restricted_keywords = "Keywords can't be blank.";
  }

  for (const [code, [lat, lon]] of Object.entries(settings.building_coords)) {
    if (!code.trim()) {
      errors.building_coords = "Building codes can't be blank.";
    } else if (!(Math.abs(lat) <= 90 && Math.abs(lon) <= 180)) {
      errors[`building_coords.${code}`] = 'Latitude must be within ±90 and longitude within ±180.';
    }
  }
  return errors;
}
