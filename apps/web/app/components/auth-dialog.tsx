"use client";

import { ArrowLeft, Eye, EyeOff, LoaderCircle, LockKeyhole } from "lucide-react";
import { FormEvent, useState } from "react";

export type AuthMode = "signin" | "signup";

type AuthPageProps = {
  mode: AuthMode;
  busy: boolean;
  error: string;
  notice: string;
  onBack: () => void;
  onNavigate: (mode: AuthMode) => void;
  onSubmit: (mode: AuthMode, email: string, password: string) => Promise<void>;
};

type FieldErrors = Partial<Record<"email" | "password" | "confirmPassword", string>>;

export function AuthPage({
  mode,
  busy,
  error,
  notice,
  onBack,
  onNavigate,
  onSubmit,
}: AuthPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      next.email = "Enter a valid email address.";
    }
    if (password.length < 8) {
      next.password = "Use at least 8 characters.";
    }
    if (mode === "signup" && password !== confirmPassword) {
      next.confirmPassword = "Passwords do not match.";
    }
    return next;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate();
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const firstField = Object.keys(nextErrors)[0] as keyof FieldErrors;
      document.getElementById(`auth-${firstField}`)?.focus();
      return;
    }
    await onSubmit(mode, email.trim(), password);
  }

  return (
    <section className="auth-page" aria-labelledby="auth-page-title">
      <div className="auth-panel">
        <button className="back-link" type="button" onClick={onBack} disabled={busy}>
          <ArrowLeft aria-hidden="true" /> Back
        </button>
        <div className="auth-mark" aria-hidden="true">
          <LockKeyhole />
        </div>
        <p className="section-kicker">Your private workspace</p>
        <h1 id="auth-page-title">{mode === "signin" ? "Log in to Resonant" : "Create your Resonant account"}</h1>
        <p className="auth-intro">
          {mode === "signin"
            ? "Return to your saved roles and skill map."
            : "Turn your resume into a focused Singapore job-search plan."}
        </p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {error ? <div className="form-alert error" role="alert">{error}</div> : null}
          {notice ? <div className="form-alert notice" role="status">{notice}</div> : null}

          <label htmlFor="auth-email">Email address</label>
          <input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="you@example.com" aria-invalid={Boolean(fieldErrors.email)} aria-describedby={fieldErrors.email ? "auth-email-error" : undefined} disabled={busy} />
          {fieldErrors.email ? <p className="field-error" id="auth-email-error">{fieldErrors.email}</p> : null}

          <label htmlFor="auth-password">Password</label>
          <div className="secret-field">
            <input id="auth-password" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "signup" ? "new-password" : "current-password"} placeholder={mode === "signup" ? "At least 8 characters" : "Your password"} aria-invalid={Boolean(fieldErrors.password)} aria-describedby={fieldErrors.password ? "auth-password-error" : mode === "signup" ? "password-help" : undefined} disabled={busy} />
            <button className="secret-toggle" type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} disabled={busy}>
              {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
            </button>
          </div>
          {fieldErrors.password ? <p className="field-error" id="auth-password-error">{fieldErrors.password}</p> : null}
          {mode === "signup" ? <p className="field-help" id="password-help">Use 8 or more characters. Password managers and paste are supported.</p> : null}

          {mode === "signup" ? (
            <>
              <label htmlFor="auth-confirmPassword">Confirm password</label>
              <input id="auth-confirmPassword" type={showPassword ? "text" : "password"} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" placeholder="Type your password again" aria-invalid={Boolean(fieldErrors.confirmPassword)} aria-describedby={fieldErrors.confirmPassword ? "auth-confirm-error" : undefined} disabled={busy} />
              {fieldErrors.confirmPassword ? <p className="field-error" id="auth-confirm-error">{fieldErrors.confirmPassword}</p> : null}
            </>
          ) : null}

          <button className="button primary auth-submit" type="submit" disabled={busy} aria-busy={busy}>
            {busy ? <LoaderCircle className="spin" aria-hidden="true" /> : null}
            <span>{mode === "signin" ? "Log in" : "Create account"}</span>
          </button>
        </form>

        <p className="auth-footer">
          {mode === "signin" ? "New to Resonant?" : "Already have an account?"}{" "}
          <button type="button" onClick={() => onNavigate(mode === "signin" ? "signup" : "signin")} disabled={busy}>
            {mode === "signin" ? "Create an account" : "Log in"}
          </button>
        </p>
      </div>
    </section>
  );
}
