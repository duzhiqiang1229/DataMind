/**
 * Module-level auth token holder.
 *
 * The Axios interceptor reads the token from here instead of localStorage,
 * avoiding the async write delay of Pinia's persist plugin.
 * The auth store calls setToken() / clearToken() to keep it in sync.
 */
let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function clearToken(): void {
  _token = null;
}
