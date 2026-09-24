export type SkillStat = {
  skill: string;
  count: number;
  percentage: number;
};

export type SalaryBucket = {
  label: string;
  count: number;
  min_salary: number;
  max_salary: number;
};

export type Resource = {
  kind: string;
  title: string;
  url: string;
  provider: string;
  skills: string[];
  description: string;
  estimated_hours?: number | null;
};

export type RoadmapStep = {
  order: number;
  title: string;
  skills: string[];
  estimated_hours: number;
  resources: Resource[];
};

export type Job = {
  id: number;
  source: string;
  title: string;
  company: string;
  location: string;
  url: string;
  salary_min?: number | null;
  salary_max?: number | null;
  currency: string;
  skills: string[];
};

export type InsightsResponse = {
  query: string;
  location: string;
  job_count: number;
  jobs: Job[];
  top_skills: SkillStat[];
  missing_skills: SkillStat[];
  salary_distribution: SalaryBucket[];
  interview_questions: Resource[];
  books: Resource[];
  courses: Resource[];
  github_projects: Resource[];
  certifications: Resource[];
  roadmap: RoadmapStep[];
  estimated_study_hours: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchInsights(input: {
  query: string;
  location: string;
  cv_skills: string[];
}): Promise<InsightsResponse> {
  const res = await fetch(`${API_URL}/api/insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: input.query,
      location: input.location,
      cv_skills: input.cv_skills,
      limit: 50,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to load insights");
  }
  return res.json();
}

export async function parseCv(file: File): Promise<string[]> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/cv/parse`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to parse CV");
  }
  const data = (await res.json()) as { skills: string[] };
  return data.skills;
}

export async function suggestRoles(query: string): Promise<RoleSuggestion[]> {
  const res = await fetch(
    `${API_URL}/api/suggest/roles?q=${encodeURIComponent(query)}&limit=8`,
  );
  if (!res.ok) return [];
  const data = (await res.json()) as { suggestions: RoleSuggestion[] };
  return data.suggestions ?? [];
}

export async function suggestLocations(query: string): Promise<string[]> {
  const res = await fetch(
    `${API_URL}/api/suggest/locations?q=${encodeURIComponent(query)}&limit=8`,
  );
  if (!res.ok) return [];
  const data = (await res.json()) as { suggestions: string[] };
  return data.suggestions ?? [];
}

export type RoleSuggestion = {
  id: number | null;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
};
