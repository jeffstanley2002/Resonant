"use client";

import {
  Bookmark,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  ExternalLink,
  FileCheck2,
  FileText,
  LoaderCircle,
  LogOut,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Star,
  Trash2,
  Upload,
  UserRound,
  Waypoints,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import type { JobMatch, MatchResponse, ResumeAnalysis, SavedJob } from "@/lib/api";

type Status = "idle" | "loading" | "error";
type TabId = "matches" | "gaps" | "saved";

type WorkspaceProps = {
  accountLabel: string;
  targetRole: string;
  location: string;
  limit: number;
  resumeText: string;
  analysis: ResumeAnalysis | null;
  result: MatchResponse | null;
  savedJobs: SavedJob[];
  status: Status;
  uploadStatus: Status;
  error: string;
  notice: string;
  turnstileEnabled: boolean;
  turnstileToken: string;
  onTargetRoleChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onLimitChange: (value: number) => void;
  onResumeTextChange: (value: string) => void;
  onUpload: (file: File | null) => Promise<void>;
  onFindMatches: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onSave: (match: JobMatch) => Promise<void>;
  onFeedback: (rating: number) => Promise<void>;
  onSignOut: () => Promise<void>;
  onDeleteData: () => Promise<boolean>;
};

const tabs: Array<{ id: TabId; label: string; icon: typeof BriefcaseBusiness }> = [
  { id: "matches", label: "Matches", icon: BriefcaseBusiness },
  { id: "gaps", label: "Skill gaps", icon: Waypoints },
  { id: "saved", label: "Saved", icon: Bookmark },
];

const ratingLabels = ["Not useful", "Slightly useful", "Useful", "Very useful", "Excellent"];

export function Workspace(props: WorkspaceProps) {
  const [activeTab, setActiveTab] = useState<TabId>("matches");
  const [visibleCount, setVisibleCount] = useState(8);
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [signOutOpen, setSignOutOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const savedIds = useMemo(() => new Set(props.savedJobs.map((job) => job.externalJobId)), [props.savedJobs]);

  const gaps = useMemo(() => aggregateGaps(props.result?.matches ?? []), [props.result]);

  function selectTab(tab: TabId) {
    setActiveTab(tab);
    document.getElementById(`tab-${tab}`)?.focus();
  }

  function onTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = tabs.length - 1;
    selectTab(tabs[nextIndex].id);
  }

  async function handleFindMatches(event: FormEvent<HTMLFormElement>) {
    setActiveTab("matches");
    setVisibleCount(8);
    setFeedbackRating(null);
    await props.onFindMatches(event);
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      if (await props.onDeleteData()) setDeleteOpen(false);
    } finally {
      setDeleting(false);
    }
  }

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await props.onSignOut();
      setSignOutOpen(false);
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <main className="app-page">
      <header className="app-header">
        <a className="brand" href="#workspace" aria-label="Resonant workspace">
          <span className="brand-mark"><Waypoints aria-hidden="true" /></span>
          <span>Resonant</span>
        </a>
        <div className="app-header-actions">
          <span className="account-label"><UserRound aria-hidden="true" />{props.accountLabel}</span>
          <button className="button header-action" type="button" onClick={() => setSignOutOpen(true)}>
            <LogOut aria-hidden="true" /> Sign out
          </button>
        </div>
      </header>

      <div className="app-layout" id="workspace">
        <aside className="setup-panel" aria-label="Search setup">
          <div className="setup-heading">
            <p className="section-kicker">Search setup</p>
            <h1>Shape your next move.</h1>
            <p>Your resume stays the source of truth for every score and suggestion.</p>
          </div>

          <section className="upload-surface" aria-labelledby="resume-upload-title">
            <div className="section-heading compact">
              <span className="section-icon"><FileText aria-hidden="true" /></span>
              <div>
                <h2 id="resume-upload-title">Resume</h2>
                <p>PDF, DOCX, or TXT up to 5 MB</p>
              </div>
            </div>
            <label className="upload-button">
              {props.uploadStatus === "loading" ? <LoaderCircle className="spin" aria-hidden="true" /> : <Upload aria-hidden="true" />}
              <span>{props.uploadStatus === "loading" ? "Analyzing resume" : "Choose resume"}</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => void props.onUpload(event.target.files?.[0] ?? null)}
                disabled={props.uploadStatus === "loading"}
              />
            </label>
            {props.analysis ? (
              <motion.div className={`resume-ready ${props.analysis.aiStatus === "failed" ? "failed" : ""}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                {props.analysis.aiStatus === "failed" ? <CircleAlert aria-hidden="true" /> : <FileCheck2 aria-hidden="true" />}
                <span>
                  {props.analysis.aiStatus === "failed" ? (
                    <><strong>AI analysis failed</strong> Retry the upload to continue</>
                  ) : (
                    <><strong>{props.analysis.skills.length} AI-verified skills</strong> ready to match</>
                  )}
                </span>
              </motion.div>
            ) : null}
          </section>

          {props.turnstileEnabled ? (
            <section className="bot-check" aria-label="Bot protection">
              <div id="turnstile-container" />
              <p><ShieldCheck aria-hidden="true" />{props.turnstileToken ? "Verification complete" : "Verify before running the agent"}</p>
            </section>
          ) : null}

          <form className="search-form" onSubmit={(event) => void handleFindMatches(event)} noValidate>
            <label htmlFor="target-role">Target role</label>
            <input id="target-role" value={props.targetRole} onChange={(event) => props.onTargetRoleChange(event.target.value)} placeholder="e.g. AI Engineer" />

            <label htmlFor="location">Location</label>
            <div className="input-with-icon">
              <MapPin aria-hidden="true" />
              <input id="location" value={props.location} onChange={(event) => props.onLocationChange(event.target.value)} placeholder="Singapore" />
            </div>

            <label htmlFor="job-limit">Recommendations</label>
            <div className="select-wrap">
              <select id="job-limit" value={props.limit} onChange={(event) => props.onLimitChange(Number(event.target.value))}>
                <option value={10}>Up to 10 roles</option>
                <option value={20}>Up to 20 roles</option>
                <option value={30}>Up to 30 roles</option>
                <option value={40}>Up to 40 roles</option>
              </select>
              <ChevronDown aria-hidden="true" />
            </div>

            <details className="resume-details">
              <summary>Review resume facts</summary>
              <label htmlFor="resume-facts">Facts used for matching</label>
              <textarea className="resize-none" id="resume-facts" value={props.resumeText} onChange={(event) => props.onResumeTextChange(event.target.value)} />
            </details>

            <button className="button primary search-submit" type="submit" disabled={props.status === "loading"} aria-busy={props.status === "loading"}>
              {props.status === "loading" ? <LoaderCircle className="spin" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
              <span>{props.status === "loading" ? "Ranking opportunities" : "Find my matches"}</span>
            </button>
          </form>

          <button className="delete-data-link" type="button" onClick={() => setDeleteOpen(true)}>
            <Trash2 aria-hidden="true" /> Delete my application data
          </button>
        </aside>

        <section className="career-workspace" aria-live="polite">
          <div className="workspace-intro">
            <div>
              <p className="section-kicker">Career signal map</p>
              <h2>{props.result?.status === "failed" ? "AI analysis did not complete" : props.result ? `${props.result.matches.length} opportunities ranked for you` : "Your focused search starts here"}</h2>
              <p>
                {props.result?.status === "failed"
                  ? "No recommendations were substituted. Review the failed stage and retry when the provider is available."
                  : props.result
                  ? "Move from evidence to gaps to action without losing the job context."
                  : "Add your resume, confirm Singapore as your location, and run the matching agent."}
              </p>
            </div>
            {props.result ? (
              <details className="run-details">
                <summary>Run details</summary>
                <dl>
                  <div><dt>Source</dt><dd>{formatSource(props.result.mode)}</dd></div>
                  <div><dt>AI status</dt><dd>{formatStatus(props.result.status)}</dd></div>
                  <div><dt>Model</dt><dd>{props.result.telemetry.model ?? "Unavailable"}</dd></div>
                  <div><dt>Estimated cost</dt><dd>${Number(props.result.telemetry.estimatedCostUsd ?? 0).toFixed(4)}</dd></div>
                </dl>
              </details>
            ) : null}
          </div>

          {props.error ? <div className="status-banner error" role="alert"><CircleAlert aria-hidden="true" />{props.error}</div> : null}
          {props.notice ? <div className="status-banner notice" role="status"><CheckCircle2 aria-hidden="true" />{props.notice}</div> : null}
          {props.result ? <AIStageSummary result={props.result} /> : null}

          <div className="workspace-tabs" role="tablist" aria-label="Career workspace">
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              const count = tab.id === "matches" ? props.result?.matches.length : tab.id === "gaps" ? gaps.length : tab.id === "saved" ? props.savedJobs.length : undefined;
              return (
                <button
                  id={`tab-${tab.id}`}
                  key={tab.id}
                  role="tab"
                  type="button"
                  aria-selected={activeTab === tab.id}
                  aria-controls={`panel-${tab.id}`}
                  tabIndex={activeTab === tab.id ? 0 : -1}
                  onClick={() => setActiveTab(tab.id)}
                  onKeyDown={(event) => onTabKeyDown(event, index)}
                >
                  <Icon aria-hidden="true" />
                  <span>{tab.label}</span>
                  {count !== undefined ? <span className="tab-count" aria-label={`${count} items`}>{count}</span> : null}
                </button>
              );
            })}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              className="tab-panel"
              id={`panel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeTab}`}
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === "matches" ? (
                <MatchesView
                  result={props.result}
                  visibleCount={visibleCount}
                  savedIds={savedIds}
                  rating={feedbackRating}
                  onLoadMore={() => setVisibleCount((current) => current + 8)}
                  onSave={props.onSave}
                  onFeedback={async (rating) => {
                    await props.onFeedback(rating);
                    setFeedbackRating(rating);
                  }}
                />
              ) : null}
              {activeTab === "gaps" ? <GapsView gaps={gaps} totalJobs={props.result?.matches.length ?? 0} /> : null}
              {activeTab === "saved" ? <SavedView jobs={props.savedJobs} /> : null}
            </motion.div>
          </AnimatePresence>
        </section>
      </div>

      <DeleteDialog open={deleteOpen} busy={deleting} onClose={() => setDeleteOpen(false)} onConfirm={() => void handleDelete()} />
      <SignOutDialog open={signOutOpen} busy={signingOut} onClose={() => setSignOutOpen(false)} onConfirm={() => void handleSignOut()} />
    </main>
  );
}

function MatchesView({
  result,
  visibleCount,
  savedIds,
  rating,
  onLoadMore,
  onSave,
  onFeedback,
}: {
  result: MatchResponse | null;
  visibleCount: number;
  savedIds: Set<string>;
  rating: number | null;
  onLoadMore: () => void;
  onSave: (match: JobMatch) => Promise<void>;
  onFeedback: (rating: number) => Promise<void>;
}) {
  if (!result) return <WorkspaceEmpty icon={BriefcaseBusiness} title="No matches yet" copy="Run your first search to see explainable scores and recommendations." />;
  if (result.status === "failed") return <WorkspaceEmpty icon={CircleAlert} title="No AI recommendations generated" copy={result.errorMessage ?? "A required AI stage failed. Retry after checking the configured model provider."} />;

  const visibleMatches = result.matches.slice(0, visibleCount);
  const usedBaselineOrder = Boolean(result.telemetry.matching_degraded_to_baseline || result.telemetry.ranking_degraded_to_baseline);
  return (
    <>
      <div className="match-toolbar">
        <p><strong>{result.matches.length}</strong> roles, ordered by {usedBaselineOrder ? "baseline score" : "AI synthesis"}</p>
        <span>Scores are directional, not hiring predictions.</span>
      </div>
      <div className="match-list">
        {visibleMatches.map((match, index) => (
          <motion.article className="match-card" key={match.job.externalId} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.035, 0.28) }}>
            <div className="match-card-head">
              <div className="rank-mark" aria-label={`Rank ${index + 1}`}>{String(index + 1).padStart(2, "0")}</div>
              <div className="job-heading">
                <h3>{match.job.title}</h3>
                <p>{match.job.company}<span aria-hidden="true">/</span>{match.job.location}</p>
              </div>
              <div className="match-score" aria-label={`${match.fitScore} percent match score`}>
                <strong>{match.fitScore}%</strong>
                <span>Match score</span>
              </div>
            </div>
            <p className="match-explanation">{match.explanation}</p>
            {match.resumeEvidence.length || match.jobEvidence.length ? (
              <div className="citation-grid" aria-label="AI evidence citations">
                {match.resumeEvidence.length ? <div><strong>Resume evidence</strong><q>{match.resumeEvidence[0]}</q></div> : null}
                {match.jobEvidence.length ? <div><strong>Role evidence</strong><q>{match.jobEvidence[0]}</q></div> : null}
              </div>
            ) : null}
            <div className="evidence-row">
              <div>
                <span className="evidence-label"><Check aria-hidden="true" />Evidence</span>
                <div className="tag-row">
                  {match.matchedSkills.length ? match.matchedSkills.slice(0, 5).map((skill) => <span className="tag evidence" key={skill}>{skill}</span>) : <span className="empty-inline">Limited direct overlap</span>}
                </div>
              </div>
              <div>
                <span className="evidence-label"><Waypoints aria-hidden="true" />Gaps</span>
                <div className="tag-row">
                  {match.missingSkills.length ? match.missingSkills.slice(0, 4).map((skill) => <span className="tag gap" key={skill}>{skill}</span>) : <span className="empty-inline">No visible priority gaps</span>}
                </div>
              </div>
            </div>
            {match.concerns.length ? <p className="match-concern"><CircleAlert aria-hidden="true" /><span><strong>Check before applying:</strong> {match.concerns.join(" ")}</span></p> : null}
            <div className="match-card-actions">
              <a className="text-link" href={match.job.url} target="_blank" rel="noreferrer">View role <ExternalLink aria-hidden="true" /></a>
              <button className="button save-button" type="button" onClick={() => void onSave(match)}>
                {savedIds.has(match.job.externalId) ? <CheckCircle2 aria-hidden="true" /> : <Bookmark aria-hidden="true" />}
                {savedIds.has(match.job.externalId) ? "Saved" : "Save role"}
              </button>
            </div>
          </motion.article>
        ))}
      </div>
      {visibleCount < result.matches.length ? (
        <button className="button load-more" type="button" onClick={onLoadMore}><RefreshCw aria-hidden="true" />Show more recommendations</button>
      ) : null}
      <section className="feedback-card" aria-labelledby="feedback-title">
        <div>
          <p className="section-kicker">Improve your results</p>
          <h3 id="feedback-title">How useful were these recommendations?</h3>
          <p>{rating ? `You rated this run: ${ratingLabels[rating - 1]}.` : "Your rating helps tune future ranking quality."}</p>
        </div>
        <div className="rating-buttons" aria-label="Recommendation usefulness rating">
          {ratingLabels.map((label, index) => {
            const value = index + 1;
            return (
              <button key={label} type="button" aria-label={`${value} out of 5: ${label}`} aria-pressed={rating === value} onClick={() => void onFeedback(value)}>
                <Star aria-hidden="true" />
                <span>{label}</span>
              </button>
            );
          })}
        </div>
      </section>
    </>
  );
}

type GapSummary = { name: string; count: number; roles: string[] };

function GapsView({ gaps, totalJobs }: { gaps: GapSummary[]; totalJobs: number }) {
  if (!totalJobs) return <WorkspaceEmpty icon={Waypoints} title="Your skill map will appear here" copy="Run a match search to see which skills repeat across your target roles." />;
  if (!gaps.length) return <WorkspaceEmpty icon={CheckCircle2} title="No repeated gaps found" copy="Your visible resume skills cover the requirements detected in these roles." />;
  return (
    <div className="gap-layout">
      <div className="insight-lead">
        <p className="section-kicker">Demand across your results</p>
        <h3>Learn what compounds.</h3>
        <p>Prioritize skills that appear across several roles instead of chasing every requirement once.</p>
      </div>
      <div className="gap-list">
        {gaps.map((gap, index) => (
          <article className="gap-item" key={gap.name}>
            <span className="gap-priority">Priority {index + 1}</span>
            <div>
              <h3>{gap.name}</h3>
              <p>Requested by <strong>{gap.count} of {totalJobs}</strong> matched roles</p>
              <span>{gap.roles.slice(0, 3).join(" / ")}</span>
            </div>
            <div className="gap-bar" aria-label={`${Math.round((gap.count / totalJobs) * 100)} percent of roles`}><span style={{ width: `${Math.max(8, (gap.count / totalJobs) * 100)}%` }} /></div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AIStageSummary({ result }: { result: MatchResponse }) {
  const incomplete = result.stages.filter((stage) => stage.status === "failed" || stage.status === "partial");
  const usedBaselineReasoning = Boolean(result.telemetry.matching_degraded_to_baseline);
  if (!incomplete.length) return null;
  return (
    <section className="ai-stage-summary" aria-labelledby="ai-stage-title">
      <div>
        <CircleAlert aria-hidden="true" />
        <div>
          <h3 id="ai-stage-title">AI run {result.status}</h3>
          <p>
            {usedBaselineReasoning
              ? "Baseline skill-overlap explanations were used where AI reasoning timed out."
              : "No deterministic text was substituted for incomplete AI work."}
          </p>
        </div>
      </div>
      <ul>
        {incomplete.map((stage) => (
          <li key={stage.stage}>
            <strong>{formatStage(stage.stage)}</strong>
            <span>{stage.message ?? formatStatus(stage.status)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SavedView({ jobs }: { jobs: SavedJob[] }) {
  if (!jobs.length) return <WorkspaceEmpty icon={Bookmark} title="No saved roles" copy="Save the opportunities you want to compare or apply to later." />;
  return (
    <div className="saved-grid">
      {jobs.map((job) => (
        <article className="saved-card" key={job.externalJobId}>
          <Bookmark aria-hidden="true" />
          <div><h3>{job.title}</h3><p>{job.company}</p></div>
          <a href={job.jobUrl} target="_blank" rel="noreferrer" aria-label={`Open ${job.title} at ${job.company}`}><ExternalLink aria-hidden="true" /></a>
        </article>
      ))}
    </div>
  );
}

function WorkspaceEmpty({ icon: Icon, title, copy }: { icon: typeof BriefcaseBusiness; title: string; copy: string }) {
  return <div className="workspace-empty"><span><Icon aria-hidden="true" /></span><h3>{title}</h3><p>{copy}</p></div>;
}

function DeleteDialog({ open, busy, onClose, onConfirm }: { open: boolean; busy: boolean; onClose: () => void; onConfirm: () => void }) {
  const ref = useRef<HTMLDialogElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      window.requestAnimationFrame(() => cancelRef.current?.focus());
    } else if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog className="confirm-dialog" ref={ref} onCancel={(event) => busy ? event.preventDefault() : onClose()} onClose={onClose} aria-labelledby="delete-title">
      <button className="icon-control dialog-close" type="button" onClick={onClose} aria-label="Close delete dialog" disabled={busy}><X aria-hidden="true" /></button>
      <span className="danger-icon"><Trash2 aria-hidden="true" /></span>
      <h2 id="delete-title">Delete your application data?</h2>
      <p>This permanently removes saved jobs, resume analyses, feedback, and agent runs. Your Supabase account remains active.</p>
      <div className="dialog-actions">
        <button className="button secondary" ref={cancelRef} type="button" onClick={onClose} disabled={busy}>Keep my data</button>
        <button className="button danger" type="button" onClick={onConfirm} disabled={busy}>{busy ? <LoaderCircle className="spin" aria-hidden="true" /> : <Trash2 aria-hidden="true" />}Delete data</button>
      </div>
    </dialog>
  );
}

function SignOutDialog({ open, busy, onClose, onConfirm }: { open: boolean; busy: boolean; onClose: () => void; onConfirm: () => void }) {
  const ref = useRef<HTMLDialogElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      window.requestAnimationFrame(() => cancelRef.current?.focus());
    } else if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog className="confirm-dialog" ref={ref} onCancel={(event) => busy ? event.preventDefault() : onClose()} onClose={onClose} aria-labelledby="signout-title">
      <button className="icon-control dialog-close" type="button" onClick={onClose} aria-label="Close sign out dialog" disabled={busy}><X aria-hidden="true" /></button>
      <span className="auth-mark" aria-hidden="true"><LogOut /></span>
      <h2 id="signout-title">Sign out of Resonant?</h2>
      <p>Your current workspace view will clear on this device. Saved roles and application data remain in your account.</p>
      <div className="dialog-actions">
        <button className="button secondary" ref={cancelRef} type="button" onClick={onClose} disabled={busy}>Stay signed in</button>
        <button className="button primary" type="button" onClick={onConfirm} disabled={busy}>{busy ? <LoaderCircle className="spin" aria-hidden="true" /> : <LogOut aria-hidden="true" />}Sign out</button>
      </div>
    </dialog>
  );
}

function aggregateGaps(matches: JobMatch[]): GapSummary[] {
  const byName = new Map<string, GapSummary>();
  matches.forEach((match) => {
    match.missingSkills.forEach((name) => {
      const current = byName.get(name) ?? { name, count: 0, roles: [] };
      current.count += 1;
      if (!current.roles.includes(match.job.title)) current.roles.push(match.job.title);
      byName.set(name, current);
    });
  });
  return [...byName.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name)).slice(0, 10);
}

function formatSource(mode: string): string {
  const labels: Record<string, string> = {
    mycareersfuture: "MyCareersFuture",
    mycareersfuture_fallback: "MyCareersFuture",
    apify_mycareersfuture: "MyCareersFuture via Apify",
    apify_mycareersfuture_fallback: "MyCareersFuture via Apify",
    adzuna: "Adzuna",
    demo: "Curated demo roles",
  };
  return labels[mode] ?? mode;
}

function formatStatus(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatStage(stage: string): string {
  return stage.split("_").map(formatStatus).join(" ");
}
