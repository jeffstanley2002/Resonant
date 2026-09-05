import { z } from "zod";

export const matchRequestSchema = z
  .object({
    resumeId: z.string().regex(/^resume_[a-fA-F0-9]{8,64}$/).optional(),
    resumeText: z.string().min(20).max(80_000).optional(),
    targetRole: z.string().min(2).max(120),
    location: z.string().min(2).max(120),
    limit: z.number().int().min(1).max(40),
  })
  .refine((value) => Boolean(value.resumeId || value.resumeText), {
    message: "Provide a resume analysis or resume text",
  });

export const feedbackSchema = z.object({
  runId: z.string().min(4).max(120),
  rating: z.number().int().min(1).max(5),
  reason: z.string().max(500).optional(),
});

export type MatchRequest = z.infer<typeof matchRequestSchema>;
export type Feedback = z.infer<typeof feedbackSchema>;

export type Skill = { name: string; category: string; confidence: number };
export type AIStatus = "succeeded" | "partial" | "failed" | "skipped";
export type AIStageResult = {
  stage: string;
  status: AIStatus;
  message?: string | null;
  processed?: number | null;
  total?: number | null;
};

export type ResumeAnalysis = {
  resumeId: string;
  summary: string;
  skills: Skill[];
  roleSignals: string[];
  seniority?: string | null;
  evidence: string[];
  uncertainties: string[];
  aiStatus: AIStatus;
  warnings: string[];
  mode: string;
  telemetry: Record<string, string | number | boolean | null>;
};

export type JobPosting = {
  externalId: string;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  source: string;
  requiredSkills: string[];
  preferredSkills: string[];
  seniority?: string | null;
  responsibilities: string[];
  domainContext: string[];
  riskFlags: string[];
  salaryMin?: number | null;
  salaryMax?: number | null;
};

export type JobMatch = {
  job: JobPosting;
  fitScore: number;
  matchedSkills: string[];
  missingSkills: string[];
  explanation: string;
  resumeEvidence: string[];
  jobEvidence: string[];
  concerns: string[];
  confidence: number;
  baselineScore?: number | null;
  aiStatus: AIStatus;
};

export type MatchResponse = {
  runId: string;
  mode: string;
  matches: JobMatch[];
  status: AIStatus;
  stages: AIStageResult[];
  errorMessage?: string | null;
  warnings: string[];
  telemetry: Record<string, string | number | boolean | null | undefined>;
};

export type SavedJob = {
  externalJobId: string;
  title: string;
  company: string;
  jobUrl: string;
  notes?: string | null;
};

export type SessionResponse = { status: string; userId: string; csrfToken: string };
export type DataDeletionResponse = { status: string; deletedTables: string[] };
