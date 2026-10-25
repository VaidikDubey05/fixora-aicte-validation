import { test, expect } from '@playwright/test';

test.describe('Admin Governance: Maker-Checker Rule Enforcement & Audit Chain Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as System Administrator User ID 1
    await page.addInitScript(() => {
      localStorage.setItem('fixora_token', 'mock_admin_token_jwt');
      localStorage.setItem(
        'fixora_user',
        JSON.stringify({
          id: 1,
          email: 'admin@aicte.gov.in',
          full_name: 'AICTE System Administrator',
          role: 'admin',
          is_active: true,
        })
      );
    });

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'admin@aicte.gov.in',
          full_name: 'AICTE System Administrator',
          role: 'admin',
          is_active: true,
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

  test('Maker-Checker Rule: author cannot approve own rule pack; independent admin can approve with UI explanation', async ({ page }) => {
    const packId = 'EOA-CHECKLIST';
    let submitCalled = false;
    let approveCalled = false;

    // Rule Pack mock: version v1.2 created by user 1 (the current user)
    await page.route(`**/api/rule-packs/${packId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: packId,
          name: 'Statutory AICTE APH Rule Specification',
          description: 'Deterministic rules for Extension of Approval scrutiny',
          status: 'In review',
          versions: [
            {
              version: 'v1.2',
              status: 'In review',
              is_active: false,
              created_by: 1, // Same as logged in admin user (id: 1)
              approved_by: null,
              checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
              created_at: new Date().toISOString(),
              rules_yaml: `pack_id: EOA-CHECKLIST\nversion: "v1.2"\nrules:\n  - id: R_LAND_01\n    name: Land Acreage\n    severity: review_required\n    condition: "payload.land_acreage >= 7.50"`,
            },
          ],
        }),
      });
    });

    await page.route(`**/api/rule-packs/${packId}/submit`, async (route) => {
      submitCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ pack_id: packId, version: 'v1.2', status: 'In review' }),
      });
    });

    await page.route(`**/api/rule-packs/${packId}/approve`, async (route) => {
      approveCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          pack_id: packId,
          version: 'v1.2',
          status: 'Approved',
          approved_by: 2,
          is_active: true,
        }),
      });
    });

    await page.goto(`/admin/rules/${packId}`, { waitUntil: 'domcontentloaded' });

    // 1. Verify Maker-Checker Restriction when User is Author:
    // Approve button MUST be disabled
    const approveBtn = page.getByRole('button', { name: 'Approve & Activate Version' });
    await expect(approveBtn).toBeVisible();
    await expect(approveBtn).toBeDisabled();

    // 2. Verify UI explains why the button is disabled
    await expect(
      page.locator('text=Maker-Checker Dual-Authorization Policy Active')
    ).toBeVisible();
    await expect(
      page.locator('text=the approving officer must differ from the author')
    ).toBeVisible();

    // 3. Maker can submit for review
    const submitBtn = page.getByRole('button', { name: 'Submit for Checker Review' });
    await expect(submitBtn).toBeVisible();

    // 4. Now simulate switching to an Independent Admin Checker (User ID: 2)
    await page.addInitScript(() => {
      localStorage.setItem(
        'fixora_user',
        JSON.stringify({
          id: 2,
          email: 'independent-admin@aicte.gov.in',
          full_name: 'Secondary Governance Auditor',
          role: 'admin',
          is_active: true,
        })
      );
    });

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 2,
          email: 'independent-admin@aicte.gov.in',
          full_name: 'Secondary Governance Auditor',
          role: 'admin',
          is_active: true,
        }),
      });
    });

    // Reload page as Independent Admin
    await page.goto(`/admin/rules/${packId}`, { waitUntil: 'domcontentloaded' });

    // Approve button MUST now be enabled because author (1) != approver (2)
    const approveBtnChecker = page.getByRole('button', { name: 'Approve & Activate Version' });
    await expect(approveBtnChecker).toBeVisible();
    await expect(approveBtnChecker).toBeEnabled();

    // Click Approve & Activate
    await approveBtnChecker.click();
    expect(approveCalled).toBe(true);
  });

  test('Cryptographic Audit Chain Integrity: verify valid chain and detect broken sequence', async ({ page }) => {
    let verifyCallCount = 0;
    let shouldSimulateTampering = false;

    await page.route('**/api/audit**', async (route) => {
      if (route.request().url().includes('/verify-chain')) {
        verifyCallCount++;
        if (shouldSimulateTampering) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              valid: false,
              checked: 35,
              first_broken_seq: 14,
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              valid: true,
              checked: 48,
              first_broken_seq: null,
            }),
          });
        }
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total: 3,
            page: 1,
            page_size: 20,
            items: [
              {
                seq: 3,
                actor: 'scrutiny@aicte.gov.in',
                role: 'scrutiny_officer',
                action: 'CONFIRM_FINDING',
                target_type: 'Finding',
                target_id: 'F-2026-001',
                payload: { action: 'confirm', reason: 'Statutory verification completed.' },
                payload_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
                prev_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
                current_hash: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
                created_at: new Date().toISOString(),
              },
              {
                seq: 2,
                actor: 'principal@gecpune.edu.in',
                role: 'institution',
                action: 'UPLOAD_DOCUMENT',
                target_type: 'Document',
                target_id: 'DOC-1',
                payload: { class_name: 'land_title_deed' },
                payload_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
                prev_hash: 'genesis_root_hash_0000000000000000000000000000000000000000000000000',
                current_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
                created_at: new Date().toISOString(),
              },
            ],
          }),
        });
      }
    });

    await page.goto('/admin/audit', { waitUntil: 'domcontentloaded' });

    // 1. Verify Header and Advisory Banner
    await expect(page.locator('text=Cryptographic Audit Chain Explorer')).toBeVisible();

    // 2. Toggle between Table View and Timeline View
    const tableToggleBtn = page.getByRole('button', { name: 'Table View' });
    await expect(tableToggleBtn).toBeVisible();
    await tableToggleBtn.click();

    // Table headers should appear
    await expect(page.locator('text=Event Action')).toBeVisible();
    await expect(page.locator('text=CONFIRM_FINDING')).toBeVisible();

    const timelineToggleBtn = page.getByRole('button', { name: 'Timeline View' });
    await timelineToggleBtn.click();
    await expect(page.locator('text=Target Resource:').first()).toBeVisible();

    // 3. Execute Valid Chain Verification
    const verifyChainBtn = page.getByRole('button', { name: 'Verify Chain Integrity' });
    await expect(verifyChainBtn).toBeVisible();
    await verifyChainBtn.click();

    // Verify Success Banner appears with block count
    await expect(
      page.locator('text=Cryptographic Audit Chain Integrity Verified')
    ).toBeVisible();
    await expect(
      page.locator('text=All 48 sequential SHA-256 blocks verified')
    ).toBeVisible();

    // 4. Test Chain Integrity Discrepancy Failure
    shouldSimulateTampering = true;
    await verifyChainBtn.click();

    // Verify Discrepancy Alert appears showing broken sequence
    await expect(
      page.locator('text=Cryptographic Audit Chain Integrity Failure!')
    ).toBeVisible();
    await expect(
      page.locator('text=Integrity broken at sequence #14')
    ).toBeVisible();
  });
});
