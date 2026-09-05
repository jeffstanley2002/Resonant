"use client";

import { ArrowRight, Bookmark, BriefcaseBusiness, Check, FileSearch, Sparkles, Waypoints } from "lucide-react";
import { motion } from "framer-motion";
import { AuthPage, type AuthMode } from "./auth-dialog";

type LandingPageProps = {
  demoMode: boolean;
  authMode: AuthMode | null;
  authBusy: boolean;
  authError: string;
  authNotice: string;
  onOpenAuth: (mode: AuthMode) => void;
  onCloseAuth: () => void;
  onAuthSubmit: (mode: AuthMode, email: string, password: string) => Promise<void>;
  onStartDemo: () => void;
};

const sequence = [
  { icon: FileSearch, label: "Resume evidence" },
  { icon: BriefcaseBusiness, label: "Ranked roles" },
  { icon: Waypoints, label: "Skill gaps" },
  { icon: Bookmark, label: "Saved roles" },
];

export function LandingPage(props: LandingPageProps) {
  if (!props.demoMode && props.authMode) {
    return (
      <main className="landing-page" id="top">
        <header className="landing-nav standalone">
          <a className="brand" href="#top" aria-label="Resonant home" onClick={props.onCloseAuth}>
            <span className="brand-mark"><Waypoints aria-hidden="true" /></span>
            <span>Resonant</span>
          </a>
          <nav aria-label="Account navigation">
            <button className="button nav-ghost" type="button" onClick={() => props.onOpenAuth(props.authMode === "signin" ? "signup" : "signin")}>
              {props.authMode === "signin" ? "Sign up" : "Log in"}
            </button>
          </nav>
        </header>
        <AuthPage
          mode={props.authMode}
          busy={props.authBusy}
          error={props.authError}
          notice={props.authNotice}
          onBack={props.onCloseAuth}
          onNavigate={props.onOpenAuth}
          onSubmit={props.onAuthSubmit}
        />
      </main>
    );
  }

  return (
    <main className="landing-page" id="top">
      <section className="landing-hero">
        <header className="landing-nav">
          <a className="brand" href="#top" aria-label="Resonant home">
            <span className="brand-mark"><Waypoints aria-hidden="true" /></span>
            <span>Resonant</span>
          </a>
          <nav aria-label="Account navigation">
            {props.demoMode ? (
              <button className="button nav-primary" type="button" onClick={props.onStartDemo}>
                Explore demo <ArrowRight aria-hidden="true" />
              </button>
            ) : (
              <>
                <button className="button nav-ghost" type="button" onClick={() => props.onOpenAuth("signin")}>Log in</button>
                <button className="button nav-primary" type="button" onClick={() => props.onOpenAuth("signup")}>Sign up</button>
              </>
            )}
          </nav>
        </header>

        <motion.div
          className="hero-copy"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        >
          <p className="hero-kicker"><Sparkles aria-hidden="true" /> Career intelligence for Singapore</p>
          <h1>Find the roles your experience is already pointing toward.</h1>
          <p>
            Upload one resume. Get explainable job matches, the skills employers keep asking for,
            and a focused shortlist for your next applications.
          </p>
          <div className="hero-actions">
            <button className="button hero-primary" type="button" onClick={props.demoMode ? props.onStartDemo : () => props.onOpenAuth("signup")}>
              {props.demoMode ? "Explore the workspace" : "Build my match plan"}
              <ArrowRight aria-hidden="true" />
            </button>
            {!props.demoMode ? (
              <button className="button hero-secondary" type="button" onClick={() => props.onOpenAuth("signin")}>I already have an account</button>
            ) : null}
          </div>
          <div className="hero-proof" aria-label="Product assurances">
            <span><Check aria-hidden="true" /> Private by design</span>
            <span><Check aria-hidden="true" /> Explainable scores</span>
            <span><Check aria-hidden="true" /> Free-tier friendly</span>
          </div>
        </motion.div>

        <motion.div
          className="signal-sequence"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.28 }}
          aria-label="How Resonant works"
        >
          {sequence.map(({ icon: Icon, label }) => (
            <div className="signal-step" key={label}>
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </div>
          ))}
        </motion.div>
      </section>

      <section className="landing-story" aria-labelledby="landing-story-title">
        <div>
          <p className="section-kicker">One search, three useful views</p>
          <h2 id="landing-story-title">A recommendation should tell you what to do next.</h2>
        </div>
        <div className="story-grid">
          <article>
            <span>01</span>
            <h3>Match with context</h3>
            <p>Every percentage is labeled and tied to visible resume evidence, not a mysterious score.</p>
          </article>
          <article>
            <span>02</span>
            <h3>See repeated gaps</h3>
            <p>Find the skills appearing across multiple roles so you know what is worth learning first.</p>
          </article>
          <article>
            <span>03</span>
            <h3>Move with a plan</h3>
            <p>Save the strongest roles and prioritize the repeated gaps before you apply.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
