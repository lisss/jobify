import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  type InsightsResponse,
  type StoredCv,
  cvDownloadUrl,
  deleteCurrentCv,
  fetchCurrentCv,
  fetchInsights,
  filterSkillsForRole,
  parseCv,
  suggestLocations,
  suggestRoles,
} from '@/lib/api'
import { InsightsPanel } from '@/components/InsightsPanel'
import { Typeahead } from '@/components/Typeahead'

export default function App() {
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [cvText, setCvText] = useState('')
  /** Full skill list from the last CV upload — re-filtered whenever role changes. */
  const [cvAllSkills, setCvAllSkills] = useState<string[]>([])
  const [storedCv, setStoredCv] = useState<StoredCv | null>(null)
  const [cvParsing, setCvParsing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [hasCvInput, setHasCvInput] = useState(false)
  const [resultKey, setResultKey] = useState(0)
  const roleFilterSeq = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadRoles = useCallback((q: string) => suggestRoles(q), [])
  const loadLocations = useCallback((q: string) => suggestLocations(q), [])

  function skillsFromTextarea(text: string): string[] {
    return Array.from(
      new Set(
        text
          .split(/[,;\n]/)
          .map((s) => s.trim())
          .filter(Boolean),
      ),
    )
  }

  // Restore CV from session cookie on load.
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const cv = await fetchCurrentCv()
        if (cancelled || !cv) return
        setStoredCv(cv)
        setCvAllSkills(cv.all_skills ?? [])
      } catch {
        // Session may be empty — ignore.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // When role changes and we have a CV skill bank, refresh the skills field.
  useEffect(() => {
    const role = query.trim()
    if (!role || cvAllSkills.length === 0) return

    const seq = ++roleFilterSeq.current
    let cancelled = false

    void (async () => {
      try {
        const skills = await filterSkillsForRole(role, cvAllSkills)
        if (cancelled || seq !== roleFilterSeq.current) return
        setCvText(skills.join(', '))
        if (skills.length === 0) {
          setError(
            'No skills from your CV match this role — add relevant ones manually.',
          )
        } else {
          setError(null)
        }
      } catch (err) {
        if (cancelled || seq !== roleFilterSeq.current) return
        setError(err instanceof Error ? err.message : 'Failed to update skills for role')
      }
    })()

    return () => {
      cancelled = true
    }
  }, [query, cvAllSkills])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const skills = skillsFromTextarea(cvText)
      const data = await fetchInsights({
        query,
        location,
        cv_skills: skills,
      })
      setHasCvInput(skills.length > 0)
      setInsights(data)
      setResultKey((k) => k + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  async function onCvUpload(file: File | null) {
    if (!file) return
    setError(null)
    setCvParsing(true)
    try {
      const role = query.trim()
      // Role is optional on upload — skills field fills once a role is chosen.
      const { skills, all_skills, cv } = await parseCv(file, role)
      setCvAllSkills(all_skills)
      if (cv) setStoredCv(cv)

      if (!role) {
        setCvText('')
        setError(null)
        return
      }

      if (skills.length === 0) {
        setCvText('')
        setError(
          'No skills in that CV match this role — add relevant ones manually below.',
        )
        return
      }
      setCvText(skills.join(', '))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CV parse failed')
    } finally {
      setCvParsing(false)
    }
  }

  async function onRemoveCv() {
    try {
      await deleteCurrentCv()
    } catch {
      // Still clear local state.
    }
    setStoredCv(null)
    setCvAllSkills([])
    setCvText('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <main className="relative z-10 mx-auto min-h-screen max-w-5xl px-5 pb-20 pt-10 sm:px-8">
      <header className="mb-12 flex items-baseline justify-between gap-4">
        <p className="text-xl font-semibold tracking-tight text-[var(--ink)]">Jobify</p>
        <p className="hidden text-sm text-[var(--muted)] sm:block">
          Role requirements and what to learn next
        </p>
      </header>

      <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-6 py-9 sm:px-9 sm:py-11">
        <h1 className="max-w-xl text-3xl font-semibold leading-tight tracking-tight text-[var(--ink)] sm:text-4xl">
          See what a role needs — and what to learn next.
        </h1>
        <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-[var(--muted)] sm:text-base">
          Pick a position and your skills. We look up books, courses, and
          interview material online for that mix.
        </p>

        <form onSubmit={onSubmit} className="relative mt-8 space-y-4">
          <div className="grid gap-3 sm:grid-cols-[1.4fr_1fr_auto]">
            <Typeahead
              label="Role"
              value={query}
              onChange={setQuery}
              fetchSuggestions={loadRoles}
              placeholder="e.g. Software Engineer"
              required
            />
            <Typeahead
              label="Location"
              value={location}
              onChange={setLocation}
              fetchSuggestions={loadLocations}
              placeholder="Remote, Berlin…"
              footerHint="Type to narrow cities worldwide"
            />
            <div className="flex items-end">
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-full rounded-xl bg-[var(--ink)] px-5 py-2.5 text-[15px] font-medium text-white transition hover:opacity-90 disabled:opacity-50 sm:w-auto"
              >
                {loading ? 'Analyzing…' : 'Get insights'}
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-sm text-[var(--muted)]">
                Your skills (comma-separated)
              </span>
              <textarea
                value={cvText}
                onChange={(e) => setCvText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    e.currentTarget.form?.requestSubmit()
                  }
                }}
                rows={3}
                placeholder={
                  cvParsing ? 'Reading skills from CV…' : 'Python, Docker, SQL…'
                }
                disabled={cvParsing}
                className="w-full resize-y rounded-xl border border-[var(--line)] bg-white px-3.5 py-2.5 text-[15px] text-[var(--ink)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] disabled:opacity-60"
              />
              {cvAllSkills.length > 0 && (
                <p className="mt-1.5 text-xs text-[var(--muted)]">
                  From your CV — updates when you change role.
                </p>
              )}
            </label>
            <div className="block">
              <span className="mb-1.5 block text-sm text-[var(--muted)]">
                CV (PDF / TXT)
              </span>
              <div className="flex min-h-[5.5rem] flex-col justify-center gap-2 rounded-xl border border-dashed border-[var(--line)] bg-[var(--surface-soft)] px-4 py-3">
                {storedCv ? (
                  <>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <a
                        href={cvDownloadUrl()}
                        className="font-medium text-[var(--ink)] underline decoration-[var(--line)] underline-offset-4 hover:decoration-[var(--accent)]"
                      >
                        {storedCv.filename}
                      </a>
                      <span className="text-xs text-[var(--muted)]">Saved in this session</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={cvParsing}
                        onClick={() => fileInputRef.current?.click()}
                        className="rounded-lg bg-[var(--ink)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
                      >
                        Replace
                      </button>
                      <button
                        type="button"
                        disabled={cvParsing}
                        onClick={() => void onRemoveCv()}
                        className="rounded-lg border border-[var(--line)] bg-white px-3 py-1.5 text-sm text-[var(--muted)] disabled:opacity-60"
                      >
                        Remove
                      </button>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-[var(--muted)]">
                    {cvParsing ? 'Uploading…' : 'No CV uploaded yet.'}
                  </p>
                )}
                {!storedCv && (
                  <button
                    type="button"
                    disabled={cvParsing}
                    onClick={() => fileInputRef.current?.click()}
                    className="w-fit rounded-lg bg-[var(--ink)] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
                  >
                    Upload CV
                  </button>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,application/pdf,text/plain"
                  disabled={cvParsing}
                  className="sr-only"
                  onChange={(e) => {
                    void onCvUpload(e.target.files?.[0] ?? null)
                    e.target.value = ''
                  }}
                />
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                {storedCv && !query.trim()
                  ? 'CV saved — select a role to fill matching skills.'
                  : query.trim() && !storedCv
                    ? `Role selected — upload a CV to fill skills for “${query.trim()}”.`
                    : query.trim() && storedCv
                      ? `Skills below are filtered for “${query.trim()}”.`
                      : 'Upload a CV and select a role (either order) to auto-fill matching skills.'}
              </p>
              {cvParsing && (
                <p className="mt-1 text-sm text-[var(--muted)]">Extracting skills…</p>
              )}
            </div>
          </div>
        </form>

        {error && (
          <p className="mt-4 rounded-xl bg-[#f8eee6] px-4 py-3 text-sm text-[var(--warn)]">
            {error}
          </p>
        )}
      </section>

      {insights && (
        <div key={resultKey} className="animate-fade mt-12">
          <InsightsPanel data={insights} showCvGaps={hasCvInput} />
        </div>
      )}
    </main>
  )
}
