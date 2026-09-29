/** Codes the API sends, plus the two the client adds for failures with no API error body. */
export type ApiErrorCode =
  | 'calendar_not_configured'
  | 'invalid_settings'
  | 'invalid_request'
  | 'upstream_unavailable'
  | 'not_found'
  | 'http_error'
  | 'network_error'
  | (string & {});

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ApiErrorCode,
    message: string,
    readonly fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function isApiError(error: unknown, code?: ApiErrorCode): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}
