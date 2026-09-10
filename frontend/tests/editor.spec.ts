import { test, expect } from '@playwright/test';
import { toneWav } from './fixtures';

test('real import, playback, processing, undo/redo, and PCM export', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('Audio service: online')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Shape your sound.' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeDisabled();
  await page.getByLabel('Import audio files').setInputFiles(toneWav());
  await expect(page.getByRole('status')).toHaveText('Import complete.');
  await expect(page.getByText('8,000 Hz')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(1);
  expect(await page.locator('canvas').evaluate(canvas => (canvas as HTMLCanvasElement).width)).toBeGreaterThan(0);
  await expect(page.getByLabel('Playback position')).toHaveAttribute('max', '2');
  await page.screenshot({ path: testInfo.outputPath('editor-dark.png'), fullPage: true });

  await page.getByRole('button', { name: 'Play', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();
  await expect.poll(async () => Number(await page.getByLabel('Playback position').inputValue())).toBeGreaterThan(0.05);
  await expect.poll(async () => await page.getByLabel('Master output peak').textContent()).not.toContain('−∞');
  await page.getByRole('button', { name: 'Go to end' }).click();
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeEnabled();
  await expect(page.getByLabel('Playback position')).toHaveValue('2');

  await page.getByRole('button', { name: 'Mute test-tone.wav', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mute test-tone.wav', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mute test-tone.wav', exact: true })).toHaveAttribute('aria-pressed', 'false');
  await page.getByLabel('Fade in seconds').fill('0.1');
  await page.getByLabel('Fade out seconds').fill('0.1');
  await page.getByRole('button', { name: 'Apply gain & fades' }).click();
  await expect(page.getByRole('status')).toHaveText('Gain and fades complete.');
  await page.getByLabel('Trim start seconds').fill('0.25');
  await page.getByLabel('Trim end seconds').fill('1.25');
  await page.getByRole('button', { name: 'Keep range' }).click();
  await expect(page.getByRole('status')).toHaveText('Trim complete.');
  await expect(page.getByLabel('Playback position')).toHaveAttribute('max', '1');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByLabel('Playback position')).toHaveAttribute('max', '2');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(page.getByLabel('Playback position')).toHaveAttribute('max', '1');

  const responsePromise = page.waitForResponse(response => response.url().endsWith('/audio/export'));
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export track', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  const stream = await download.createReadStream();
  expect(stream).not.toBeNull();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const wav = Buffer.concat(chunks);
  expect(wav.toString('ascii', 0, 4)).toBe('RIFF');
  expect(wav.readUInt16LE(20)).toBe(1);
  expect(wav.readUInt16LE(22)).toBe(2);
  expect(wav.readUInt32LE(24)).toBe(8000);
  expect(wav.readUInt16LE(34)).toBe(16);
  expect(download.suggestedFilename()).toBe('test-tone-soniccraft.wav');
  await expect(page.getByRole('status')).toHaveText('Export complete.');
  expect(errors).toEqual([]);
});

test('failed and canceled imports do not change the session; reconnect is available', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Import audio files').setInputFiles({ name: 'invalid.wav', mimeType: 'audio/wav', buffer: Buffer.from('not audio') });
  await expect(page.getByRole('alert')).toContainText('Cannot decode');
  await expect(page.getByRole('heading', { name: 'Shape your sound.' })).toBeVisible();
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  let release: () => void = () => {};
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/audio/inspect', async route => {
    await held;
    await route.abort().catch(() => {});
  });
  await page.getByLabel('Import audio files').setInputFiles(toneWav());
  await expect(page.getByRole('status')).toHaveText('Import…');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Operation canceled');
  await expect(page.getByRole('heading', { name: 'Shape your sound.' })).toBeVisible();
  release();
  await page.unroute('**/audio/inspect');
  await page.route('**/health', route => route.abort());
  await page.reload();
  await expect(page.getByText('Audio service: offline')).toBeVisible();
  await page.unroute('**/health');
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await expect(page.getByText('Audio service: online')).toBeVisible();
  await page.getByLabel('Import audio files').setInputFiles(toneWav());
  await expect(page.getByRole('status')).toHaveText('Import complete.');
});

test('track controls and processing remain accessible in both themes on narrow screens', async ({ page }, testInfo) => {
  await page.goto('/');
  await page.getByLabel('Import audio files').setInputFiles(toneWav());
  await expect(page.getByRole('status')).toHaveText('Import complete.');
  await page.getByLabel('Track name', { exact: true }).fill('Lecture recording');
  await page.getByLabel('Track name', { exact: true }).press('Tab');
  await expect(page.getByRole('button', { name: 'Remove Lecture recording' })).toBeEnabled();
  await page.getByRole('button', { name: 'Switch to light theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  for (const width of [1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('button', { name: 'Apply gain & fades' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Export track' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Open audio', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('editor-light-' + width + '.png'), fullPage: true });
  }
});
