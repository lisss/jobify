import type { InsightsResponse, Resource } from '@/lib/api'

function SectionTitle({
  children,
  prominent = false,
}: {
  children: React.ReactNode
  prominent?: boolean
}) {
  if (prominent) {
    return (
      <h3 className="text-2xl font-bold tracking-tight text-[var(--ink)] sm:text-[1.65rem]">
        {children}
      </h3>
    )
  }
  return <h3 className="text-lg font-semibold tracking-tight">{children}</h3>
}

function ResourceList({
  title,
  items,
  empty,
  prominent = false,
}: {
  title: string
  items: Resource[]
  empty: string
  prominent?: boolean
}) {
  return (
    <section>
      <SectionTitle prominent={prominent}>{title}</SectionTitle>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--muted)]">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {items.map((item) => (
            <li
              key={`${item.kind}-${item.title}`}
              className="border-b border-[var(--line)] pb-3 last:border-0"
            >
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium underline decoration-[var(--line)] underline-offset-4 hover:decoration-[var(--accent)]"
                >
                  {item.title}
                </a>
              ) : (
                <p className="font-medium">{item.title}</p>
              )}
              <p className="mt-1 text-sm text-[var(--muted)]">
                {[item.provider, item.description].filter(Boolean).join(' — ')}
              </p>
              {item.estimated_hours != null && (
                <p className="mt-1 text-xs text-[var(--ok)]">~{item.estimated_hours}h</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function InsightsPanel({
  data,
  showCvGaps = false,
}: {
  data: InsightsResponse
  showCvGaps?: boolean
}) {
  const maxImportance = Math.max(...data.requirements.map((s) => s.percentage), 1)
  const matched = new Set(data.matched_skills ?? [])
  const partial = new Set(data.partial_skills ?? [])
  const stackSkills = [
    ...(data.matched_skills ?? []),
    ...(data.unmatched_cv_skills ?? []),
  ]

  function coverageOf(skill: string): 'covered' | 'partial' | 'missing' | null {
    if (!showCvGaps) return null
    if (matched.has(skill)) return 'covered'
    if (partial.has(skill)) return 'partial'
    return 'missing'
  }

  function coverageLabel(status: 'covered' | 'partial' | 'missing') {
    if (status === 'covered') return 'covered'
    if (status === 'partial') return 'partial'
    return 'missing'
  }

  function coverageColor(status: 'covered' | 'partial' | 'missing' | null) {
    if (status === 'covered') return 'var(--ok)'
    if (status === 'partial') return 'var(--partial)'
    if (status === 'missing') return 'var(--missing)'
    return 'var(--accent)'
  }

  function coverageTextClass(status: 'covered' | 'partial' | 'missing') {
    if (status === 'covered') return 'text-[var(--ok)]'
    if (status === 'partial') return 'text-[var(--partial)]'
    return 'text-[var(--missing)]'
  }

  return (
    <div className="space-y-10">
      <div>
        <p className="text-sm text-[var(--muted)]">Position</p>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {data.query}
          {data.location ? ` · ${data.location}` : ''}
        </h2>
      </div>

      {showCvGaps && stackSkills.length > 0 && (
        <div className="rounded-2xl border border-[var(--line)] bg-white px-5 py-4 sm:px-6">
          <p className="text-sm text-[var(--ink)]">
            Learning path personalized for:{' '}
            <span className="font-medium">{stackSkills.join(', ')}</span>
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Materials mix your stack with what this role typically still needs.
          </p>
        </div>
      )}

      <div className={`grid gap-8 ${showCvGaps ? 'lg:grid-cols-2' : ''}`}>
        <section>
          <SectionTitle prominent>Role requirements</SectionTitle>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {showCvGaps
              ? 'Green = covered, yellow = related skill, red = still missing.'
              : 'Typical skills for this position, ranked by importance.'}
          </p>
          <ul className="mt-4 space-y-3">
            {data.requirements.map((skill) => {
              const status = coverageOf(skill.skill)
              return (
                <li key={skill.skill}>
                  <div className="mb-1 flex justify-between gap-3 text-sm">
                    <span className="font-medium">
                      {skill.skill}
                      {status && (
                        <span
                          className={`ml-2 text-xs font-normal ${coverageTextClass(status)}`}
                        >
                          {coverageLabel(status)}
                        </span>
                      )}
                    </span>
                    <span className="shrink-0 text-[var(--muted)]">{skill.percentage}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-soft)]">
                    <div
                      className="skill-bar h-full rounded-full"
                      style={{
                        width: `${(skill.percentage / maxImportance) * 100}%`,
                        backgroundColor: coverageColor(status),
                      }}
                    />
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        {showCvGaps && (
          <section>
            <SectionTitle>Still to learn for this role</SectionTitle>
            {data.missing_skills.length === 0 ? (
              <p className="mt-3 text-sm text-[var(--muted)]">
                No major role gaps — focus on deepening your stack below.
              </p>
            ) : (
              <ul className="mt-4 flex flex-wrap gap-2">
                {data.missing_skills.map((skill) => (
                  <li
                    key={skill.skill}
                    className="rounded-lg border border-[var(--line)] bg-white px-3 py-1.5 text-sm"
                  >
                    <span className="font-medium">{skill.skill}</span>
                    <span className="ml-2 text-[var(--muted)]">{skill.percentage}%</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>

      <section className="rounded-2xl border border-[var(--line)] bg-white px-6 py-7 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <SectionTitle prominent>Learning roadmap</SectionTitle>
          <p className="text-sm text-[var(--muted)]">
            ~{data.estimated_study_hours} hours estimated
          </p>
        </div>
        <p className="mt-2 text-sm text-[var(--muted)]">
          {showCvGaps
            ? 'Starts from your skills, then covers role gaps.'
            : 'Based on typical requirements for this role.'}
        </p>
        <ol className="mt-6 space-y-5">
          {data.roadmap.map((step) => (
            <li key={step.order} className="grid gap-2 sm:grid-cols-[2.5rem_1fr]">
              <span className="text-lg font-medium text-[var(--muted)]">
                {String(step.order).padStart(2, '0')}
              </span>
              <div>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-[var(--muted)]">
                  {step.skills.join(' · ')} · ~{step.estimated_hours}h
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-10 md:grid-cols-2">
        <ResourceList
          title="Books"
          items={data.books}
          empty="No books matched this role and skill mix yet."
          prominent
        />
        <ResourceList
          title="Courses"
          items={data.courses}
          empty="No courses matched this role and skill mix yet."
          prominent
        />
        <ResourceList
          title="Certifications"
          items={data.certifications}
          empty="No certifications matched this role and skill mix."
        />
        <ResourceList
          title="Interview questions"
          items={data.interview_questions}
          empty="No interview prompts yet."
        />
      </div>
    </div>
  )
}
