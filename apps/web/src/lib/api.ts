export type SkillStat = {
  skill: string
  count: number
  percentage: number
}

export type Resource = {
  kind: string
  title: string
  url: string
  provider: string
  skills: string[]
  description: string
  estimated_hours?: number | null
}

export type RoadmapStep = {
  order: number
  title: string
  skills: string[]
  estimated_hours: number
  resources: Resource[]
}

export type InsightsResponse = {
  query: string
  location?: string
  requirements: SkillStat[]
  matched_skills: string[]
  partial_skills: string[]
  missing_skills: SkillStat[]
  unmatched_cv_skills: string[]
  interview_questions: Resource[]
  books: Resource[]
  courses: Resource[]
  certifications: Resource[]
  roadmap: RoadmapStep[]
  estimated_study_hours: number
}

export type StoredCv = {
  id: string
  filename: string
  content_type: string
  uploaded_at: string
  download_url: string
  all_skills: string[]
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

/** Session cookie must travel with CV requests. */
const withSession: RequestInit = { credentials: 'include' }

export function cvDownloadUrl(): string {
  return `${API_URL}/api/cv/download`
}

export async function fetchInsights(input: {
  query: string
  cv_skills: string[]
}): Promise<InsightsResponse> {
  const res = await fetch(`${API_URL}/api/insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: input.query,
      cv_skills: input.cv_skills,
    }),
    ...withSession,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to load insights')
  }
  return res.json()
}

export async function parseCv(
  file: File,
  role: string,
): Promise<{ skills: string[]; all_skills: string[]; cv: StoredCv | null }> {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  if (role.trim()) params.set('role', role.trim())
  const qs = params.toString()
  const res = await fetch(`${API_URL}/api/cv/parse${qs ? `?${qs}` : ''}`, {
    method: 'POST',
    body: form,
    ...withSession,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to parse CV')
  }
  const data = (await res.json()) as {
    skills: string[]
    all_skills?: string[]
    cv?: StoredCv
  }
  return {
    skills: data.skills ?? [],
    all_skills: data.all_skills ?? data.skills ?? [],
    cv: data.cv ?? null,
  }
}

export async function fetchCurrentCv(): Promise<StoredCv | null> {
  const res = await fetch(`${API_URL}/api/cv/current`, withSession)
  if (!res.ok) return null
  const data = (await res.json()) as { cv: StoredCv | null }
  return data.cv ?? null
}

export async function deleteCurrentCv(): Promise<void> {
  await fetch(`${API_URL}/api/cv/current`, { method: 'DELETE', ...withSession })
}

export async function filterSkillsForRole(
  role: string,
  skills: string[],
): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/cv/skills/for-role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, skills }),
    ...withSession,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to filter skills')
  }
  const data = (await res.json()) as { skills: string[] }
  return data.skills ?? []
}

export async function suggestRoles(query: string): Promise<string[]> {
  const res = await fetch(
    `${API_URL}/api/suggest/roles?q=${encodeURIComponent(query)}&limit=12`,
    withSession,
  )
  if (!res.ok) return []
  const data = (await res.json()) as { suggestions: string[] }
  return data.suggestions ?? []
}
