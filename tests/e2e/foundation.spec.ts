import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

test('real registration, workspace, project, settings, persistence, and offline recovery', async ({
  page,
}) => {
  const failures: string[] = [];
  page.on('pageerror', (error) => failures.push(error.message));
  const email = `preview-${Date.now()}@example.com`;
  const password = 'foundation-test-password-2026';
  await mkdir('docs/screenshots', { recursive: true });
  await page.goto('/');
  await expect(page.getByLabel('Email address')).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/m1-sign-up.png' });
  await page.getByLabel('Your name').fill('Alex Morgan');
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create your account', exact: true }).click();
  await page.getByRole('button', { name: 'Create your workspace', exact: true }).click();
  await page.getByLabel('Workspace name', { exact: true }).fill('Northstar Engineering');
  await page.getByRole('button', { name: 'Create workspace', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Close dialog' })).toBeHidden();
  await expect(page.getByText('Your systems, in focus.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Add project', exact: true }).click();
  await page.getByLabel('Project name', { exact: true }).fill('checkout-api');
  await page.getByRole('button', { name: 'Create project', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Close dialog' })).toBeHidden();
  await expect(
    page.getByRole('button', { name: 'Select project checkout-api', exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/m1-overview-mobile.png' });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await expect(page.getByText('YOUR COMMAND CENTER', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/m1-overview-desktop.png' });
  await page.getByRole('tab', { name: 'Settings', exact: true }).click();
  await expect(page.getByText('production', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Add environment', exact: true }).click();
  await page.getByLabel('Environment name', { exact: true }).fill('staging');
  await page.getByRole('button', { name: 'Create environment', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Close dialog' })).toBeHidden();
  await expect(page.getByText('staging', { exact: true })).toBeVisible();
  await page.getByRole('radio', { name: 'dark theme', exact: true }).click();
  await page.getByRole('tab', { name: 'Overview', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByText('YOUR COMMAND CENTER', { exact: true })).toBeHidden();
  await expect(page.getByText('Your systems, in focus.', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/m1-overview-dark.png' });
  await page.getByRole('tab', { name: 'Incidents', exact: true }).click();
  await expect(page.getByText('INGESTION NOT ENABLED', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Activity', exact: true }).click();
  await expect(page.getByText('workspace / create', { exact: true })).toBeVisible();
  // Reload discards web-preview credentials; sign back in and verify server persistence.
  await page.reload();
  await page.getByRole('tab', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in to Faultline', exact: true }).click();
  await page.getByRole('tab', { name: 'Settings', exact: true }).click();
  await expect(page.getByText('staging', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByLabel('Email address')).toBeVisible();
  // A transport failure produces a useful, recoverable state without a fabricated login.
  await page.route('**/auth/login', (route) => route.abort());
  await page.getByRole('tab', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in to Faultline', exact: true }).click();
  await expect(page.getByText(/Cannot reach Faultline/)).toBeVisible();
  await page.unroute('**/auth/login');
  await page.getByRole('button', { name: 'Sign in to Faultline', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Select project checkout-api', exact: true }),
  ).toBeVisible();
  expect(failures).toEqual([]);
});
