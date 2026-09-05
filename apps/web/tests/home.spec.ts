import { expect, test, type Page } from "@playwright/test";

const apiHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization,content-type,x-csrf-token,x-turnstile-token",
  "Access-Control-Allow-Methods": "DELETE,GET,POST,OPTIONS",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/saved-jobs", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", headers: apiHeaders, body: JSON.stringify([]) });
      return;
    }
    await route.fallback();
  });
});

async function enterDemoWorkspace(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: /explore the workspace/i }).click();
}

test("opens with a focused landing page and enters the workspace", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /find the roles your experience/i })).toBeVisible();
  await expect(page.getByText("Career intelligence for Singapore")).toBeVisible();
  await expect(page.getByText("Resume evidence", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /explore the workspace/i }).click();
  await expect(page.getByRole("heading", { name: "Shape your next move." })).toBeVisible();
  await expect(page.getByLabel("Location")).toHaveValue("Singapore");
  await expect(page.getByLabel("Recommendations")).toHaveValue("30");
  await expect(page.getByRole("tab", { name: /skill gaps/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /coaching/i })).toHaveCount(0);
});

test("renders explained matches, skill gaps, feedback, and saved roles", async ({ page }) => {
  await page.route("**/agent/matches", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        run_id: "run_test",
        mode: "demo",
        status: "succeeded",
        stages: [],
        matches: [
          {
            job: {
              external_id: "job_1",
              title: "AI Engineer",
              company: "SignalWorks",
              location: "Singapore",
              description: "Python LangGraph FastAPI Postgres",
              url: "https://example.com/job",
              source: "demo",
            },
            fit_score: 94,
            matched_skills: ["Python", "LangGraph"],
            missing_skills: ["Postgres"],
            explanation: "Strong fit based on visible AI engineering skills",
            resume_evidence: ["Python and LangGraph"],
            job_evidence: ["Python LangGraph FastAPI"],
            concerns: ["Postgres is not shown in the resume."],
            confidence: 0.9,
            baseline_score: 88,
            ai_status: "succeeded",
          },
        ],
        warnings: [],
        telemetry: { model: "test/model", provider: "test", model_fallback: false, estimated_cost_usd: 0.0004 },
      }),
    });
  });

  await page.route("**/saved-jobs", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", headers: apiHeaders, body: JSON.stringify([]) });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({ external_job_id: "job_1", title: "AI Engineer", company: "SignalWorks", job_url: "https://example.com/job" }),
    });
  });

  await page.route("**/feedback", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    await route.fulfill({ contentType: "application/json", headers: apiHeaders, body: JSON.stringify({ status: "accepted" }) });
  });

  await enterDemoWorkspace(page);
  await page.getByRole("button", { name: /find my matches/i }).click();

  await expect(page.getByLabel("94 percent match score")).toContainText("Match score");
  await expect(page.getByText("Scores are directional, not hiring predictions.")).toBeVisible();
  await page.getByRole("button", { name: /save role/i }).click();

  await page.getByRole("tab", { name: /skill gaps/i }).click();
  await expect(page.getByText("Requested by")).toBeVisible();
  await expect(page.getByText("1 of 1")).toBeVisible();

  await page.getByRole("tab", { name: /matches/i }).click();
  await page.getByRole("button", { name: /5 out of 5: excellent/i }).click();
  await expect(page.getByText(/you rated this run: excellent/i)).toBeVisible();

  await page.getByRole("tab", { name: /saved/i }).click();
  await expect(page.getByRole("heading", { name: "AI Engineer" })).toBeVisible();
});

test("analyzes an uploaded resume and updates resume facts", async ({ page }) => {
  let matchRequest: Record<string, unknown> | null = null;
  await page.route("**/resumes/analyze", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        resume_id: "resume_deadbeef",
        summary: "AI engineer with Python and Supabase experience.",
        ai_status: "succeeded",
        role_signals: ["AI Engineer"],
        evidence: ["Python", "Supabase"],
        uncertainties: [],
        skills: [
          { name: "Python", category: "backend", confidence: 0.9 },
          { name: "Supabase", category: "database", confidence: 0.8 },
        ],
        warnings: [],
      }),
    });
  });
  await page.route("**/agent/matches", async (route) => {
    matchRequest = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        run_id: "run_resume_id",
        mode: "demo",
        status: "succeeded",
        stages: [],
        matches: [],
        warnings: [],
        telemetry: {},
      }),
    });
  });

  await enterDemoWorkspace(page);
  await page.locator("input[type=file]").setInputFiles({ name: "resume.txt", mimeType: "text/plain", buffer: Buffer.from("Python Supabase AI engineer") });
  await expect(page.getByText("2 AI-verified skills")).toBeVisible();
  await page.getByText("Review resume facts").click();
  await expect(page.getByLabel("Facts used for matching")).toHaveValue(/AI engineer with Python and Supabase experience/i);
  await page.getByRole("button", { name: /find my matches/i }).click();
  await expect.poll(() => matchRequest).not.toBeNull();
  expect(matchRequest).toMatchObject({ resume_id: "resume_deadbeef" });
  expect(matchRequest).not.toHaveProperty("resume_text");
});

test("uses uploaded resume facts inline when analysis storage fails", async ({ page }) => {
  let matchRequest: Record<string, unknown> | null = null;
  await page.route("**/resumes/analyze", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        resume_id: "resume_deadbeef",
        summary: "AI engineer with Python and Supabase experience.",
        ai_status: "succeeded",
        role_signals: ["AI Engineer"],
        evidence: ["Python", "Supabase"],
        uncertainties: [],
        skills: [
          { name: "Python", category: "backend", confidence: 0.9 },
          { name: "Supabase", category: "database", confidence: 0.8 },
        ],
        warnings: ["Resume was analyzed, but saving failed. Matching will use extracted facts for this session."],
        telemetry: { storage_persisted: false },
      }),
    });
  });
  await page.route("**/agent/matches", async (route) => {
    matchRequest = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        run_id: "run_inline_resume",
        mode: "demo",
        status: "succeeded",
        stages: [],
        matches: [],
        warnings: [],
        telemetry: {},
      }),
    });
  });

  await enterDemoWorkspace(page);
  await page.locator("input[type=file]").setInputFiles({ name: "resume.txt", mimeType: "text/plain", buffer: Buffer.from("Python Supabase AI engineer") });
  await page.getByRole("button", { name: /find my matches/i }).click();
  await expect.poll(() => matchRequest).not.toBeNull();
  const postedMatchRequest = matchRequest as unknown as Record<string, unknown>;
  expect(postedMatchRequest).not.toHaveProperty("resume_id");
  expect(postedMatchRequest.resume_text).toContain("AI engineer with Python and Supabase experience.");
});

test("shows an explicit failed AI stage without synthetic recommendations", async ({ page }) => {
  await page.route("**/agent/matches", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({
        run_id: "run_failed_ai",
        mode: "unavailable",
        status: "failed",
        matches: [],
        stages: [{
          stage: "resume_analysis",
          status: "failed",
          message: "AI analysis is unavailable because no model provider is configured.",
        }],
        error_message: "AI analysis is unavailable because no model provider is configured.",
        warnings: [],
        telemetry: { model: "unavailable", provider: "none", model_fallback: true },
      }),
    });
  });

  await enterDemoWorkspace(page);
  await page.getByRole("button", { name: /find my matches/i }).click();

  await expect(page.getByRole("heading", { name: "AI analysis did not complete" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "No AI recommendations generated" })).toBeVisible();
  await expect(page.getByText("No deterministic text was substituted for incomplete AI work.")).toBeVisible();
});

test("uses an app dialog before deleting application data", async ({ page }) => {
  await page.route("**/account/data", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: apiHeaders });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      headers: apiHeaders,
      body: JSON.stringify({ status: "deleted", deleted_tables: ["resume_analyses", "job_matches", "job_searches", "saved_jobs", "feedback", "agent_runs"] }),
    });
  });

  await enterDemoWorkspace(page);
  await page.getByRole("button", { name: /delete my application data/i }).click();
  const dialog = page.getByRole("dialog", { name: /delete your application data/i });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Delete data" }).click();
  await expect(page.getByText("Deleted 6 application data groups.")).toBeVisible();
});
