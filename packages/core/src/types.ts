// Friendly names for the API contract. schema.ts is generated from the FastAPI OpenAPI
// schema (`npm run gen:types` at the repo root) — never edit it by hand.
import type { components } from './schema';

type Schemas = components['schemas'];

export type Settings = Schemas['Settings'];
export type RecommendationRequest = Schemas['RecommendationRequest'];
export type RecommendationsResponse = Schemas['RecommendationsResponse'];
export type Recommendation = Schemas['RecommendationOut'];
export type PlateItem = Schemas['PlateItem'];
export type Nutrition = Schemas['Nutrition'];
export type Scores = Schemas['Scores'];
export type Window = Schemas['Window'];
export type Goal = Schemas['Goal'];
export type MealsResponse = Schemas['MealsResponse'];
export type MetaResponse = Schemas['MetaResponse'];
export type CalendarSource = MetaResponse['calendar_source'];
export type ErrorBody = Schemas['ErrorBody'];
