import { describe, it, expect } from 'vitest';
import { apiGet, apiPost, setToken, getToken } from '../api.js';

describe('api client', () => {
  it('setToken and getToken work', () => {
    setToken('test-token-123');
    expect(getToken()).toBe('test-token-123');
    setToken(null);
    expect(getToken()).toBeNull();
  });
});
