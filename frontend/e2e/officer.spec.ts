import { test, expect } from '@playwright/test';

test.describe('Officer Scrutiny Workspace & Adjudication Protocol', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as scrutiny officer
    await page.addInitScript(() => {
      localStorage.setItem('fixora_token', 'mock_officer_token_jwt');
      localStorage.setItem(
        'fixora_user',
        JSON.stringify({
          id: 'user-officer-1',
          email: 'scrutiny@aicte.gov.in',
          full_name: 'Senior Scrutiny Officer',
          role: 'scrutiny_officer',
          is_active: true,
        })
      );
    });

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-officer-1',
          email: 'scrutiny@aicte.gov.in',
          full_name: 'Senior Scrutiny Officer',
          role: 'scrutiny_officer',
          is_active: true,
        }),
      });
    });

    await page.route('**/api/documents/*/pages/*/image', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(''),
      });
    });

    await page.route('**/api/documents/*/ocr', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'DOC-LAND-01',
          page_width: 800,
          page_height: 1000,
          tokens: [],
        }),
      });
    });

    await page.route('**/api/alerts**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], unread_count: 0 }),
      });
    });
  });

  test('Open a case and verify three-pane workspace integration', async ({ page }) => {
    const appId = 'APP-EOA-2026-00102';

    await page.route(`**/api/applications/${appId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: appId,
          institution_id: '1-33276541',
          institution_name: 'Government College of Engineering, Pune',
          state: 'READY_FOR_SCRUTINY',
          category: 'ENGINEERING_AND_TECHNOLOGY',
          academic_year: '2026-2027',
          priority_score: 75.0,
          documents: [
            { id: 'DOC-LAND-01', filename: 'land_deed.pdf', class: 'land_title_deed', page_count: 3 },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/checklist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          checklist: [
            { name: 'Land Title Acreage Requirement', status: 'compliant' },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/findings`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          findings: [
            {
              finding_id: 'F-2026-001',
              title: 'Land Title Acreage Discrepancy',
              reason: 'Declared acreage is 7.42 acres while deed states 7.10 acres.',
              severity: 'CRITICAL',
              type: 'INCONSISTENT',
              confidence: 96.4,
              status: 'open',
              evidence: [
                {
                  kind: 'region',
                  document_id: 'DOC-LAND-01',
                  page: 1,
                  bbox: [10, 20, 30, 40],
                  field: 'Land Acreage',
                  value: '7.42 Acres',
                  threshold: '7.50 Acres Min',
                },
              ],
            },
          ],
        }),
      });
    });

    await page.goto(`/officer/applications/${appId}`, { waitUntil: 'domcontentloaded' });

    // Verify Three-Pane layout elements
    // Left pane
    await expect(page.locator('text=Findings (1)')).toBeVisible();
    await expect(page.locator('text=Statutory Checklist Health')).toBeVisible();

    // Center pane (Evidence Viewer)
    await expect(page.locator('text=land_deed.pdf')).toBeVisible();
    await expect(page.locator('button:has-text("OCR Stream")')).toBeVisible();

    // Right pane (Adjudication panel & Mandatory label)
    await expect(page.locator('text=Preliminary indicator - human verification required')).toBeVisible();
    await expect(page.locator('text=Reason & Ground Truth Telemetry')).toBeVisible();
    await expect(page.locator('text=Compared Evidence Values')).toBeVisible();
  });

  test('Confirm one finding and dismiss another with mandatory >=10 char written reasons', async ({ page }) => {
    const appId = 'APP-EOA-2026-00102';
    let findingActions: any[] = [];

    await page.route(`**/api/applications/${appId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: appId,
          institution_id: '1-33276541',
          institution_name: 'Government College of Engineering, Pune',
          state: 'UNDER_OFFICIAL_REVIEW',
          priority_score: 82.0,
          documents: [
            { id: 'DOC-1', filename: 'land_deed.pdf', class: 'land_title_deed', page_count: 2 },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/checklist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ application_id: appId, checklist: [] }),
      });
    });

    await page.route(`**/api/applications/${appId}/findings`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          findings: [
            {
              finding_id: 'F-2026-001',
              title: 'Land Parcel Contiguity Check',
              reason: 'Contiguity affidavit requires state revenue verification.',
              severity: 'MAJOR',
              type: 'INCONSISTENT',
              confidence: 94.0,
              status: 'open',
              evidence: [{ kind: 'record', field: 'Contiguity', value: 'Single plot' }],
            },
            {
              finding_id: 'F-2026-002',
              title: 'Fire NOC Certificate Expiry',
              reason: 'Date stamped on certificate requires municipal confirmation.',
              severity: 'MODERATE',
              type: 'EXPIRED',
              confidence: 92.5,
              status: 'open',
              evidence: [{ kind: 'record', field: 'NOC Date', value: '2026-03-31' }],
            },
          ],
        }),
      });
    });

    // Capture POST findings/:id/actions
    await page.route('**/api/findings/*/actions', async (route) => {
      const payload = route.request().postDataJSON();
      findingActions.push(payload);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, action: payload.action }),
      });
    });

    await page.goto(`/officer/applications/${appId}`, { waitUntil: 'domcontentloaded' });

    // Select Finding 1 & Click Confirm [C]
    await page.click('button:has-text("Confirm [C]")');

    // Verify Decision Modal is open
    await expect(page.locator('text=Officer Decision: Confirm Finding')).toBeVisible();

    const recordBtn = page.locator('button:has-text("Record Adjudication")');
    const reasonInput = page.locator('textarea[placeholder*="Cite relevant AICTE"]');

    // Verify disabled when reason is < 10 characters
    await reasonInput.fill('Short');
    await expect(recordBtn).toBeDisabled();
    await expect(page.locator('text=Min 10 characters required')).toBeVisible();

    // Fill valid reason >= 10 chars
    await reasonInput.fill('Statutory land deed title confirmed against state revenue records.');
    await expect(recordBtn).toBeEnabled();
    await recordBtn.click();

    // Verify modal closed without page reload
    await expect(page.locator('text=Officer Decision: Confirm Finding')).not.toBeVisible();
    expect(findingActions.length).toBe(1);
    expect(findingActions[0].action).toBe('confirm');

    // Now select Finding 2 via next finding button or list
    await page.click('text=Fire NOC Certificate Expiry');
    await page.click('button:has-text("Dismiss [D]")');

    await expect(page.locator('text=Officer Decision: Dismiss Finding')).toBeVisible();
    const reasonInput2 = page.locator('textarea[placeholder*="Cite relevant AICTE"]');
    const recordBtn2 = page.locator('button:has-text("Record Adjudication")');

    // Verify disabled until >= 10 chars
    await reasonInput2.fill('Too brief');
    await expect(recordBtn2).toBeDisabled();

    await reasonInput2.fill('Certificate was renewed with state municipal portal under receipt 89201.');
    await expect(recordBtn2).toBeEnabled();
    await recordBtn2.click();

    await expect(page.locator('text=Officer Decision: Dismiss Finding')).not.toBeVisible();
    expect(findingActions.length).toBe(2);
    expect(findingActions[1].action).toBe('dismiss');
  });

  test('Retry statutory verification against external registry gateway', async ({ page }) => {
    let verifyRetried = false;

    await page.route('**/api/verification/queue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          total: 1,
          items: [
            {
              record_id: 101,
              document_id: 'DOC-LAND-091',
              application_id: 'APP-EOA-2026-00102',
              class_name: 'land_title_deed',
              status: 'SOURCE_UNAVAILABLE',
              source_name: 'State IGR Land Title Registry',
              simulated: true,
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    await page.route('**/api/documents/DOC-LAND-091/verify', async (route) => {
      verifyRetried = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'DOC-LAND-091',
          status: 'VERIFIED',
          simulated: true,
        }),
      });
    });

    await page.goto('/officer/verification');

    await expect(page.locator('text=Verification Bureau Gateway')).toBeVisible();
    await expect(page.locator('text=A source outage is never an adverse conclusion')).toBeVisible();

    // Click retry statutory verification icon button
    const retryBtn = page.locator('button[title="Retry Statutory Verification"]');
    await expect(retryBtn).toBeVisible();
    await retryBtn.click();

    expect(verifyRetried).toBe(true);
  });

  test('Request statutory rectification from review workspace', async ({ page }) => {
    const appId = 'APP-EOA-2026-00102';
    let rectificationAction: any = null;

    await page.route(`**/api/applications/${appId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: appId,
          institution_name: 'Government College of Engineering, Pune',
          state: 'UNDER_OFFICIAL_REVIEW',
          priority_score: 80.0,
          documents: [{ id: 'DOC-1', filename: 'fire_noc.pdf' }],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/checklist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ application_id: appId, checklist: [] }),
      });
    });

    await page.route(`**/api/applications/${appId}/findings`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          findings: [
            {
              finding_id: 'F-2026-099',
              title: 'Expired Fire Safety NOC Clearance',
              reason: 'NOC valid through August 2026. Renewal certificate required.',
              severity: 'CRITICAL',
              type: 'EXPIRED',
              status: 'open',
              evidence: [],
            },
          ],
        }),
      });
    });

    await page.route('**/api/findings/*/actions', async (route) => {
      rectificationAction = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, action: 'request_rectification' }),
      });
    });

    await page.goto(`/officer/applications/${appId}`, { waitUntil: 'domcontentloaded' });

    // Click Rectify button
    await page.click('button:has-text("Rectify")');

    await expect(page.locator('text=Officer Decision: Request Rectification')).toBeVisible();
    const reasonInput = page.locator('textarea[placeholder*="Cite relevant AICTE"]');
    await reasonInput.fill('Please upload renewed Fire Department NOC within 48 hours for scrutiny clearance.');

    const submitBtn = page.locator('button:has-text("Record Adjudication")');
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    await expect(page.locator('text=Officer Decision: Request Rectification')).not.toBeVisible();
    expect(rectificationAction).not.toBeNull();
    expect(rectificationAction.action).toBe('request_rectification');
  });
});
