import { InsightsResponse, Resource } from "@/lib/api";

function formatSalary(job: InsightsResponse["jobs"][number]) {
  if (job.salary_min == null && job.salary_max == null) return "—";
  const cur = job.currency || "USD";
  if (job.salary_min != null && job.salary_max != null) {
    return `${cur} ${Math.round(job.salary_min / 1000)}k–${Math.round(job.salary_max / 1000)}k`;
  }
  const v = job.salary_min ?? job.salary_max ?? 0;
  return `${cur} ${Math.round(v / 1000)}k`;
}

function SectionTitle({
  children,
  prominent = false,
}: {
  children: React.ReactNode;
  prominent?: boolean;
}) {
  if (prominent) {
    return (
      <h3 className="text-2xl font-bold tracking-tight text-[var(--ink)] sm:text-[1.65rem]">
        {children}
      </h3>
    );
  }
  return <h3 className="text-lg font-semibold tracking-tight">{children}</h3>;
}

function ResourceList({
  title,
  items,
  empty,
  prominent = false,
}: {
  title: string;
  items: Resource[];
  empty: string;
  prominent?: boolean;
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
                {[item.provider, item.description].filter(Boolean).join(" — ")}
              </p>
              {item.estimated_hours != null && (
                <p className="mt-1 text-xs text-[var(--ok)]">~{item.estimated_hours}h</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function InsightsPanel({ data }: { data: InsightsResponse }) {
  const maxSkill = Math.max(...data.top_skills.map((s) => s.percentage), 1);
  const maxSalaryCount = Math.max(...data.salary_distribution.map((b) => b.count), 1);

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-[var(--muted)]">Insights for</p>
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {data.query}
            {data.location ? ` · ${data.location}` : ""}
          </h2>
        </div>
        <div className="rounded-xl bg-[var(--surface-soft)] px-4 py-3 text-[var(--ink)]">
          <p className="text-xl font-semibold">{data.job_count}</p>
          <p className="text-xs text-[var(--muted)]">jobs matched</p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <SectionTitle>Skills in these jobs</SectionTitle>
          <ul className="mt-4 space-y-3">
            {data.top_skills.slice(0, 12).map((skill) => (
              <li key={skill.skill}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="font-medium">{skill.skill}</span>
                  <span className="text-[var(--muted)]">{skill.percentage}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-soft)]">
                  <div
                    className="skill-bar h-full rounded-full bg-[var(--ok)]"
                    style={{ width: `${(skill.percentage / maxSkill) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <SectionTitle>Missing from your CV</SectionTitle>
          {data.missing_skills.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--muted)]">
              No major gaps detected — your listed skills cover the frequent ones.
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

          <div className="mt-8">
            <SectionTitle>Salary distribution</SectionTitle>
          </div>
          {data.salary_distribution.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--muted)]">
              Not enough salary data in this sample.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.salary_distribution.map((bucket) => (
                <li key={bucket.label}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{bucket.label}</span>
                    <span className="text-[var(--muted)]">{bucket.count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-soft)]">
                    <div
                      className="skill-bar h-full rounded-full bg-[var(--accent)]"
                      style={{ width: `${(bucket.count / maxSalaryCount) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-[var(--line)] bg-white px-6 py-7 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <SectionTitle prominent>Learning roadmap</SectionTitle>
          <p className="text-sm text-[var(--muted)]">
            ~{data.estimated_study_hours} hours estimated
          </p>
        </div>
        <ol className="mt-6 space-y-5">
          {data.roadmap.map((step) => (
            <li key={step.order} className="grid gap-2 sm:grid-cols-[2.5rem_1fr]">
              <span className="text-lg font-medium text-[var(--muted)]">
                {String(step.order).padStart(2, "0")}
              </span>
              <div>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-[var(--muted)]">
                  {step.skills.join(" · ")} · ~{step.estimated_hours}h
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
          empty="No books matched yet."
          prominent
        />
        <ResourceList
          title="Courses"
          items={data.courses}
          empty="No courses matched yet."
          prominent
        />
        <ResourceList
          title="Certifications"
          items={data.certifications}
          empty="No certifications matched — often a good sign they don’t matter for this cluster."
        />
        <ResourceList
          title="Interview questions"
          items={data.interview_questions}
          empty="No interview prompts yet."
        />
      </div>

      <section>
        <SectionTitle>Matching jobs</SectionTitle>
        <ul className="mt-4 divide-y divide-[var(--line)]">
          {data.jobs.slice(0, 20).map((job) => (
            <li
              key={job.id}
              className="flex flex-col gap-1 py-4 sm:flex-row sm:items-baseline sm:justify-between"
            >
              <div>
                {job.url ? (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium underline decoration-[var(--line)] underline-offset-4 hover:decoration-[var(--accent)]"
                  >
                    {job.title}
                  </a>
                ) : (
                  <p className="font-medium">{job.title}</p>
                )}
                <p className="text-sm text-[var(--muted)]">
                  {job.company} · {job.location || "—"} · {job.source}
                </p>
              </div>
              <p className="text-sm">{formatSalary(job)}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
