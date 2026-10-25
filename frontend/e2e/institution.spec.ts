import { test, expect } from '@playwright/test';

test.describe('Institution Portal Experience & Statutory Guardrails', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication profile as institution user
    await page.addInitScript(() => {
      localStorage.setItem('fixora_token', 'mock_inst_token_jwt');
      localStorage.setItem(
        'fixora_user',
        JSON.stringify({
          id: 'user-inst-1',
          email: 'principal@gecpune.edu.in',
          full_name: 'Government College of Engineering, Pune',
          role: 'institution',
          institution_id: '1-33276541',
          is_active: true,
        })
      );
    });
  });

  test('Create, validate, and submit a statutory application dossier', async ({ page }) => {
    // Intercept backend API calls for hermetic reliable testing
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-inst-1',
          email: 'principal@gecpune.edu.in',
          full_name: 'Government College of Engineering, Pune',
          role: 'institution',
          institution_id: '1-33276541',
          is_active: true,
        }),
      });
    });

    let createdId = 'APP-EOA-2026-TEST01';
    await page.route('**/api/applications', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: createdId,
            state: 'DRAFT',
            academic_year: '2026-2027',
            institution_id: '1-33276541',
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      }
    });

    await page.route(`**/api/applications/${createdId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: createdId,
          institution_id: '1-33276541',
          institution_name: 'Government College of Engineering, Pune',
          state: 'DRAFT',
          category: 'ENGINEERING_AND_TECHNOLOGY',
          academic_year: '2026-2027',
          documents: [
            { id: 'DOC-1', filename: 'land_deed.pdf', class: 'land_title_deed', page_count: 3 },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${createdId}/checklist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: createdId,
          results: [
            { rule_id: 'R_LAND_01', result: 'COMPLIANT', inputs: { document_class: 'land_title_deed' } },
            { rule_id: 'R_FIRE_01', result: 'PENDING', inputs: { document_class: 'fire_safety_certificate' } },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${createdId}/validate`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'validation_completed',
          application_id: createdId,
          state: 'VALIDATION_IN_PROGRESS',
        }),
      });
    });

    await page.route(`**/api/applications/${createdId}/status`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: createdId,
          is_running: false,
          progress_pct: 100,
          current_stage: 'Verify',
        }),
      });
    });

    await page.route(`**/api/applications/${createdId}/findings`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: createdId,
          findings: [],
        }),
      });
    });

    await page.route(`**/api/applications/${createdId}/submit`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: createdId,
          state: 'SUBMITTED',
          submitted_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto('/institution/applications/new', { waitUntil: 'domcontentloaded' });

    // Step 1: Institutional Metadata
    await expect(page.locator('text=Step 1: Institutional Metadata')).toBeVisible();
    await page.click('button:has-text("Continue to Intake & Land")');

    // Step 2: Intake & Land
    await expect(page.locator('text=Step 2: Academic Programs, Land & Faculty')).toBeVisible();
    await page.click('button:has-text("Proceed to Document Uploads")');

    // Step 3: Dossier Uploads
    await expect(page.locator('text=Step 3: Statutory Dossier Uploads')).toBeVisible();
    await page.click('button:has-text("Run Automated Validation Checks")');

    // Step 4: Automated Validation Pipeline
    await expect(page.locator('text=Step 4: Automated Validation Pipeline')).toBeVisible();
    await expect(page.locator('text=No Deficiencies Found')).toBeVisible();
    await page.click('button:has-text("Review & Transmit Dossier")');

    // Step 5: Final Submission
    await expect(page.locator('text=Step 5: Final Review & Transmission')).toBeVisible();
    await page.click('button:has-text("Submit Dossier to AICTE Scrutiny Bureau")');

    // Verification of redirect to application detail
    await expect(page).toHaveURL(new RegExp(`/institution/applications/${createdId}`));
  });

  test('Fix a missing document by uploading replacement annexure', async ({ page }) => {
    const appId = 'APP-EOA-2026-RECT02';

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-inst-1',
          email: 'principal@gecpune.edu.in',
          role: 'institution',
          institution_id: '1-33276541',
          is_active: true,
        }),
      });
    });

    await page.route(`**/api/applications/${appId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: appId,
          institution_id: '1-33276541',
          institution_name: 'Government College of Engineering, Pune',
          state: 'RECTIFICATION_REQUESTED',
          category: 'ENGINEERING_AND_TECHNOLOGY',
          academic_year: '2026-2027',
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
        body: JSON.stringify({
          application_id: appId,
          results: [
            { rule_id: 'R_FIRE_NOC', result: 'MISSING', inputs: { document_class: 'fire_safety_certificate' } },
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
              finding_id: 'F-2026-0041',
              title: 'Mandatory Fire Safety NOC Clearance Missing',
              reason: 'No municipal fire safety NOC found in application repository.',
              severity: 'CRITICAL',
              type: 'MISSING',
              evidence: [{ field: 'fire_safety_certificate', kind: 'record' }],
            },
          ],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/documents`, async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'DOC-NEW-FIRE',
          class_name: 'fire_safety_certificate',
          version: 2,
          rectification_revalidated: true,
        }),
      });
    });

    await page.goto(`/institution/applications/${appId}`, { waitUntil: 'domcontentloaded' });

    // Check tabs exist
    await expect(page.getByRole('button', { name: 'Statutory Checklist' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deficiencies' })).toBeVisible();

    // Click Deficiencies Tab
    await page.click('button:has-text("Deficiencies")');
    await expect(page.locator('text=Mandatory Fire Safety NOC Clearance Missing')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Upload Compliant Replacement' })).toBeVisible();

    // Click to jump to replacement form in Documents tab
    await page.getByRole('button', { name: 'Upload Compliant Replacement' }).click();
    await expect(page.locator('text=Upload Additional or Replacement Annexure')).toBeVisible();
  });

  test('Statutory Visibility Guarantee: institution NEVER sees anomalies, priority scores, or internal notes', async ({ page }) => {
    const appId = 'APP-EOA-2026-AUDIT03';

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-inst-1',
          email: 'principal@gecpune.edu.in',
          role: 'institution',
          institution_id: '1-33276541',
          is_active: true,
        }),
      });
    });

    // Provide payload containing simulated adverse indicators that MUST BE FILTERED OUT
    await page.route(`**/api/applications/${appId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: appId,
          institution_id: '1-33276541',
          institution_name: 'Government College of Engineering, Pune',
          state: 'RECTIFICATION_REQUESTED',
          category: 'ENGINEERING_AND_TECHNOLOGY',
          academic_year: '2026-2027',
          // priority_score is None for institution
          priority_score: null,
          documents: [],
        }),
      });
    });

    await page.route(`**/api/applications/${appId}/checklist`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          results: [],
        }),
      });
    });

    // Findings API returning both allowed and disallowed findings
    await page.route(`**/api/applications/${appId}/findings`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          application_id: appId,
          findings: [
            {
              finding_id: 'F-ALLOWED-01',
              title: 'Building Occupancy Renewal Due',
              reason: 'Municipal occupancy certificate requires annual renewal stamp.',
              severity: 'MODERATE',
              type: 'EXPIRED',
              evidence: [],
            },
            {
              finding_id: 'F-BLOCKED-01',
              title: 'Possible Anomaly in Land Deed Font',
              reason: 'EXIF metadata discrepancy flagged by ML model.',
              severity: 'CRITICAL',
              type: 'possible_anomaly', // MUST NEVER APPEAR IN INSTITUTION UI
              evidence: [],
            },
            {
              finding_id: 'F-BLOCKED-02',
              title: 'Duplicate Faculty UID',
              reason: 'Faculty member claimed by two institutions.',
              severity: 'CRITICAL',
              type: 'duplicate', // MUST NEVER APPEAR IN INSTITUTION UI
              evidence: [],
            },
          ],
        }),
      });
    });

    await page.goto(`/institution/applications/${appId}`);

    // Verify allowed plain-language deficiency is displayed
    await page.click('button:has-text("Deficiencies")');
    await expect(page.locator('text=Building Occupancy Renewal Due')).toBeVisible();

    // STRICT INVARIANTS: Assert disallowed content is NEVER rendered
    await expect(page.locator('text=Possible Anomaly in Land Deed Font')).not.toBeVisible();
    await expect(page.locator('text=possible_anomaly')).not.toBeVisible();
    await expect(page.locator('text=Duplicate Faculty UID')).not.toBeVisible();
    await expect(page.locator('text=Priority Index')).not.toBeVisible();
    await expect(page.locator('text=Priority Score')).not.toBeVisible();
    await expect(page.locator('text=internal notes')).not.toBeVisible();

    // Verify timeline tab shows institution-safe lifecycle progression
    await page.click('button:has-text("Timeline & History")');
    await expect(page.locator('text=Application Lifecycle Status Progression')).toBeVisible();
    await expect(page.locator('text=Verified Statutory Dossier Activity Log')).toBeVisible();
  });
});
