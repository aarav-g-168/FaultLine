import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  timeout: 90000,
  use: {
    baseURL: 'http://localhost:8081',
    viewport: { width: 390, height: 844 },
    trace: 'retain-on-failure',
  },
  reporter: 'list',
});
