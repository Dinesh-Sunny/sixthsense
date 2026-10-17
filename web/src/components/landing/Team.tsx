"use client";

import { Reveal, rise, stagger } from "@/components/landing/reveal";
import { TEAM } from "@/components/landing/team";
import { assetUrl, cn } from "@/lib/utils";

/**
 * 4:5 portrait. The warm placeholder with initials sits underneath; the photo is a background image on top,
 * so a missing file simply leaves the placeholder (never a broken-image icon).
 */
function Portrait({ name, photo }: { name: string; photo: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2);
  return (
    <div className="dusk-card relative aspect-[4/5] w-full overflow-hidden rounded-xl shadow-float">
      <span aria-hidden className="absolute inset-0 grid place-items-center font-serif text-[96px] leading-none text-ink/25">
        {initials}
      </span>
      <span
        role="img"
        aria-label={`Portrait of ${name}`}
        className="absolute inset-0 bg-cover bg-top transition-transform duration-200 ease-out group-hover/team:scale-[1.03]"
        style={{ backgroundImage: `url(${assetUrl(photo)})` }}
      />
    </div>
  );
}

export function Team({ actions }: { actions?: React.ReactNode }) {
  return (
    <section aria-labelledby="team-h" className="mx-auto max-w-[1200px] px-4 py-12 md:px-10 md:py-16 lg:px-[80px]">
      <Reveal>
        <h2 id="team-h" className={cn("mb-8 text-center font-serif text-[36px] leading-[1.08] md:text-[44px]", rise)}>
          Team
        </h2>
        <ul className="mx-auto grid max-w-[760px] grid-cols-1 gap-8 sm:grid-cols-2">
          {TEAM.map((t, n) => (
            <li key={t.name} className={cn("group/team flex flex-col items-center gap-3 text-center", rise)} style={stagger(n + 1)}>
              <Portrait name={t.name} photo={t.photo} />
              <div className="font-serif text-[32px] leading-tight">{t.name}</div>
              <p className="text-body-sm text-ink-muted">{t.role}</p>
              {t.linkedin && (
                <a
                  href={t.linkedin}
                  target="_blank"
                  rel="noreferrer"
                  className="link-grow pb-0.5 text-body-sm font-medium text-ink"
                >
                  LinkedIn →
                </a>
              )}
            </li>
          ))}
        </ul>
        {actions && (
          <div className={cn("mt-10 flex flex-wrap items-center justify-center gap-3", rise)} style={stagger(TEAM.length + 1)}>
            {actions}
          </div>
        )}
      </Reveal>
    </section>
  );
}
