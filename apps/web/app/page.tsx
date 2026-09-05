"use client";

import Script from "next/script";
import { MotionConfig } from "framer-motion";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { AuthMode } from "./components/auth-dialog";
import { LandingPage } from "./components/landing-page";
import { Workspace } from "./components/workspace";
import {
  analyzeResume,
  clearBackendSession,
  createMatches,
  deleteAccountData,
  demoResume,
  establishBackendSession,
  listSavedJobs,
  saveJob,
  submitFeedback,
  type JobMatch,
  type MatchResponse,
  type ResumeAnalysis,
  type SavedJob,
} from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { getSupabaseClient } from "@/lib/supabase";

type Status = "idle" | "loading" | "error";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          theme: "dark";
          callback: (token: string) => void;
          "expired-callback": () => void;
          "error-callback": () => void;
        },
      ) => string;
      reset: (widgetId?: string) => void;
    };
  }
}

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";
const TURNSTILE_ENABLED = Boolean(TURNSTILE_SITE_KEY) && !TURNSTILE_SITE_KEY.toLowerCase().includes("optional");

export default function Home() {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [authResolved, setAuthResolved] = useState(false);
  const [accountLabel, setAccountLabel] = useState("Demo workspace");
  const [authMode, setAuthMode] = useState<AuthMode | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [demoStarted, setDemoStarted] = useState(false);
  const [resumeText, setResumeText] = useState(demoResume);
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [targetRole, setTargetRole] = useState("AI Engineer");
  const [location, setLocation] = useState("Singapore");
  const [limit, setLimit] = useState(30);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [uploadStatus, setUploadStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [turnstileReady, setTurnstileReady] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState("");
  const turnstileWidgetIdRef = useRef<string | null>(null);

  const supabase = getSupabaseClient();
  const authLoading = Boolean(supabase) && !authResolved;
  const authRequired = Boolean(supabase) && authResolved && !authToken;
  const showLanding = authLoading || authRequired || (!supabase && !demoStarted);

  const refreshSavedJobs = useCallback(async (token: string | null) => {
    setSavedJobs(await listSavedJobs(token));
  }, []);

  useEffect(() => {
    if (!supabase) return;
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      const session = data.session;
      setAuthToken(session?.access_token ?? null);
      setAccountLabel(session?.user.email ?? "Signed out");
      if (session?.access_token) {
        void establishBackendSession(session.access_token).then((backendSession) => setCsrfToken(backendSession?.csrfToken ?? null));
        void refreshSavedJobs(session.access_token);
      } else {
        setCsrfToken(null);
        setSavedJobs([]);
      }
      setAuthResolved(true);
    }).catch(() => {
      if (!active) return;
      setAuthToken(null);
      setCsrfToken(null);
      setAccountLabel("Signed out");
      setSavedJobs([]);
      setAuthResolved(true);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthToken(session?.access_token ?? null);
      setAccountLabel(session?.user.email ?? "Signed out");
      setAuthResolved(true);
      if (session?.access_token) {
        void establishBackendSession(session.access_token).then((backendSession) => setCsrfToken(backendSession?.csrfToken ?? null));
        void refreshSavedJobs(session.access_token);
      } else {
        setCsrfToken(null);
        setSavedJobs([]);
      }
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [refreshSavedJobs, supabase]);

  useEffect(() => {
    const container = document.getElementById("turnstile-container");
    if (!TURNSTILE_ENABLED || !turnstileReady || !container || turnstileWidgetIdRef.current || !window.turnstile) return;
    turnstileWidgetIdRef.current = window.turnstile.render(container, {
      sitekey: TURNSTILE_SITE_KEY,
      theme: "dark",
      callback: (token: string) => setTurnstileToken(token),
      "expired-callback": () => setTurnstileToken(""),
      "error-callback": () => setTurnstileToken(""),
    });
  }, [authToken, turnstileReady]);

  const resetTurnstile = useCallback(() => {
    if (!TURNSTILE_ENABLED) return;
    setTurnstileToken("");
    window.turnstile?.reset(turnstileWidgetIdRef.current ?? undefined);
  }, []);

  function openAuth(mode: AuthMode) {
    if (authToken) {
      setError("You are already logged in. Sign out before creating or using another account.");
      setNotice("");
      return;
    }
    setAuthMode(mode);
    setError("");
    setNotice("");
  }

  async function onAuth(mode: AuthMode, email: string, password: string) {
    if (!supabase) return;
    setAuthBusy(true);
    setError("");
    setNotice("");
    try {
      const currentSession = (await supabase.auth.getSession()).data.session;
      if (currentSession?.access_token) {
        setAuthToken(currentSession.access_token);
        setAccountLabel(currentSession.user.email ?? "Signed in");
        setNotice("You are already logged in. Sign out before switching accounts.");
        setAuthMode(null);
        return;
      }
      if (mode === "signup") {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
        if (signUpError) {
          setError(signUpError.message);
          return;
        }
        if (data.user && Array.isArray(data.user.identities) && data.user.identities.length === 0) {
          setError("An account already exists for this email. Log in instead, or use password recovery if you cannot access it.");
          return;
        }
        if (!data.session?.access_token) {
          setNotice("If this is a new account, check your email to confirm it, then return here to log in.");
          return;
        }
        setAuthToken(data.session.access_token);
        setAccountLabel(data.user?.email ?? email);
        const backendSession = await establishBackendSession(data.session.access_token);
        setCsrfToken(backendSession?.csrfToken ?? null);
        setAuthMode(null);
        trackEvent("user_authenticated", { mode: "supabase_signup" });
        return;
      }

      const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError || !data.session?.access_token) {
        setError("Email or password is incorrect. Check your details and try again.");
        return;
      }
      setAuthToken(data.session.access_token);
      setAccountLabel(data.user.email ?? email);
      const backendSession = await establishBackendSession(data.session.access_token);
      setCsrfToken(backendSession?.csrfToken ?? null);
      setAuthMode(null);
      trackEvent("user_authenticated", { mode: "supabase" });
    } finally {
      setAuthBusy(false);
    }
  }

  async function onSignOut() {
    await clearBackendSession(csrfToken);
    setCsrfToken(null);
    setAuthToken(null);
    setAccountLabel("Signed out");
    setSavedJobs([]);
    setResult(null);
    setAnalysis(null);
    turnstileWidgetIdRef.current = null;
    if (supabase) await supabase.auth.signOut();
    else setDemoStarted(false);
    trackEvent("user_signed_out", { mode: supabase ? "supabase" : "demo" });
  }

  async function onUpload(file: File | null) {
    if (!file) return;
    setUploadStatus("loading");
    setError("");
    setNotice("");
    if (TURNSTILE_ENABLED && !turnstileToken) {
      setUploadStatus("error");
      setError("Complete the bot check before uploading a resume.");
      return;
    }
    trackEvent("resume_upload_started", { file_type: file.type, size_bucket: sizeBucket(file.size) });
    try {
      const response = await analyzeResume(file, authToken, turnstileToken, csrfToken);
      setAnalysis(response);
      if (response.aiStatus === "failed") {
        setUploadStatus("error");
        setError(response.warnings.at(-1) ?? "Resume text was parsed, but AI analysis failed.");
        trackEvent("resume_ai_analysis_failed", { mode: response.mode });
      } else {
        setResumeText(`${response.summary}\nSkills: ${response.skills.map((skill) => skill.name).join(", ")}`);
        setUploadStatus("idle");
        setNotice("Resume analyzed. Your search is ready to run.");
        trackEvent("resume_upload_completed", { skill_count: response.skills.length });
      }
    } catch (caught) {
      setUploadStatus("error");
      const message = caught instanceof Error ? caught.message : "Resume upload failed";
      setError(message);
      trackEvent("resume_upload_failed", { reason: message.slice(0, 80) });
    } finally {
      resetTurnstile();
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (targetRole.trim().length < 2 || location.trim().length < 2) {
      setError("Enter a target role and location before finding matches.");
      return;
    }
    if (analysis?.aiStatus === "failed") {
      setError("Resume text was parsed, but AI analysis failed. Retry the resume analysis before matching.");
      return;
    }
    if (TURNSTILE_ENABLED && !turnstileToken) {
      setError("Complete the bot check before ranking jobs.");
      return;
    }
    setStatus("loading");
    trackEvent("job_search_started", { target_role: targetRole, limit });
    try {
      const response = await createMatches({
        resumeId:
          analysis?.aiStatus === "succeeded" && analysis.telemetry?.storagePersisted !== false
            ? analysis.resumeId
            : undefined,
        resumeText:
          !analysis || analysis.telemetry?.storagePersisted === false ? resumeText : undefined,
        targetRole: targetRole.trim(),
        location: location.trim(),
        limit,
        token: authToken,
        botToken: turnstileToken,
        csrfToken,
      });
      setResult(response);
      if (response.status === "failed") {
        setStatus("error");
        setError(response.errorMessage ?? "AI analysis failed. No recommendations were generated.");
        trackEvent("job_search_failed", { stage: response.stages.find((stage) => stage.status === "failed")?.stage ?? "unknown" });
      } else {
        setStatus("idle");
        if (response.status === "partial") {
          setNotice("Some AI stages were incomplete. Available results are clearly marked below.");
        }
        trackEvent("job_search_completed", { mode: response.mode, match_count: response.matches.length, status: response.status });
      }
    } catch (caught) {
      setStatus("error");
      const message = caught instanceof Error ? caught.message : "Unable to rank jobs";
      setError(message);
      trackEvent("job_search_failed", { reason: message.slice(0, 80) });
    } finally {
      resetTurnstile();
    }
  }

  async function onSave(match: JobMatch) {
    setError("");
    try {
      const saved = await saveJob(match, authToken, csrfToken);
      setSavedJobs((current) => [saved, ...current.filter((job) => job.externalJobId !== saved.externalJobId)]);
      setNotice(`${match.job.title} saved.`);
      trackEvent("job_saved", { source: match.job.source });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save this role");
    }
  }

  async function onFeedback(rating: number) {
    if (!result) return;
    setError("");
    try {
      await submitFeedback(result.runId, rating, authToken, csrfToken);
      setNotice("Thanks. Your recommendation rating was saved.");
      trackEvent("recommendation_feedback_submitted", { rating });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save your rating");
    }
  }

  async function onDeleteData(): Promise<boolean> {
    setError("");
    setNotice("");
    try {
      const response = await deleteAccountData(authToken, csrfToken);
      setAnalysis(null);
      setResult(null);
      setSavedJobs([]);
      setNotice(`Deleted ${response.deletedTables.length} application data groups.`);
      trackEvent("account_data_deleted", { table_count: response.deletedTables.length });
      return true;
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unable to delete account data";
      setError(message);
      trackEvent("account_data_delete_failed", { reason: message.slice(0, 80) });
      return false;
    }
  }

  return (
    <MotionConfig reducedMotion="user">
      {TURNSTILE_ENABLED ? <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onLoad={() => setTurnstileReady(true)} /> : null}
      {showLanding ? (
        <LandingPage
          demoMode={!supabase}
          authMode={authMode}
          authBusy={authBusy || authLoading}
          authError={error}
          authNotice={notice}
          onOpenAuth={openAuth}
          onCloseAuth={() => {
            setAuthMode(null);
            setError("");
            setNotice("");
          }}
          onAuthSubmit={onAuth}
          onStartDemo={() => setDemoStarted(true)}
        />
      ) : (
        <Workspace
          accountLabel={accountLabel}
          targetRole={targetRole}
          location={location}
          limit={limit}
          resumeText={resumeText}
          analysis={analysis}
          result={result}
          savedJobs={savedJobs}
          status={status}
          uploadStatus={uploadStatus}
          error={error}
          notice={notice}
          turnstileEnabled={TURNSTILE_ENABLED}
          turnstileToken={turnstileToken}
          onTargetRoleChange={setTargetRole}
          onLocationChange={setLocation}
          onLimitChange={setLimit}
          onResumeTextChange={(value) => {
            setResumeText(value);
            setAnalysis(null);
          }}
          onUpload={onUpload}
          onFindMatches={onSubmit}
          onSave={onSave}
          onFeedback={onFeedback}
          onSignOut={onSignOut}
          onDeleteData={onDeleteData}
        />
      )}
    </MotionConfig>
  );
}

function sizeBucket(bytes: number): string {
  if (bytes < 250_000) return "small";
  if (bytes < 2_000_000) return "medium";
  return "large";
}
