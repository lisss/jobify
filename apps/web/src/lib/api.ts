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
  location: string
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

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export async function fetchInsights(input: {
  query: string
  location: string
  cv_skills: string[]
}): Promise<InsightsResponse> {
  const res = await fetch(`${API_URL}/api/insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: input.query,
      location: input.location,
      cv_skills: input.cv_skills,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to load insights')
  }
  return res.json()
}

export async function parseCv(file: File): Promise<string[]> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_URL}/api/cv/parse`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to parse CV')
  }
  const data = (await res.json()) as { skills: string[] }
  return data.skills
}

export async function suggestRoles(query: string): Promise<string[]> {
  const res = await fetch(
    `${API_URL}/api/suggest/roles?q=${encodeURIComponent(query)}&limit=12`,
  )
  if (!res.ok) return []
  const data = (await res.json()) as { suggestions: string[] }
  return data.suggestions ?? []
}

export async function suggestLocations(query: string): Promise<string[]> {
  const res = await fetch(
    `${API_URL}/api/suggest/locations?q=${encodeURIComponent(query)}&limit=50`,
  )
  if (!res.ok) return []
  const data = (await res.json()) as { suggestions: string[] }
  return data.suggestions ?? []
}
