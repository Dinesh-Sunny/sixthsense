"use client";

import { Reveal, rise, stagger } from "@/components/landing/reveal";
import { TEAM } from "@/components/landing/team";
import { assetUrl, cn } from "@/lib/utils";

function Avatar({ name, photo }: { name: string; photo: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2);
  // Initials sit underneath; the photo covers them once it loads (a missing file shows the initials).
  return (
    <div className="relative size-24 overflow-hidden shrink-0 rounded-full bg-surface-sunk shadow-float">
      <span aria-hidden className="absolute inset-0 grid place-items-center font-serif text-[32px] text-ink-muted">
        {initials}
      </span>
      {/* Background image, not <img>: a missing file simply shows the initials, with no broken-image icon. */}
      <span
        role="img"
        aria-label={`Portrait of ${name}`}
        className="relative block size-full rounded-full bg-cover bg-center transition-transform duration-200 ease-out group-hover/team:scale-[1.03]"
        style={{ backgroundImage: `url(${assetUrl(photo)})` }}
      />
    </div>
  );
}

export function Team() {
  return (
    <section aria-labelledby="team-h" className="mx-auto max-w-[1200px] px-4 py-16 md:px-10 md:py-24 lg:px-[80px]">
      <Reveal>
        <h2 id="team-h" className={cn("mb-8 font-serif text-[36px] leading-[1.08] md:text-[44px]", rise)}>
          Team
        </h2>
        <ul className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {TEAM.map((t, n) => (
            <li key={t.name} className={cn(rise)} style={stagger(n + 1)}>
              <div className="group/team lift flex h-full items-center gap-5 rounded-xl bg-surface p-6 shadow-float">
                <Avatar name={t.name} photo={t.photo} />
                <div className="flex min-w-0 flex-col gap-1.5">
                  <div className="font-serif text-[26px] leading-tight">{t.name}</div>
                  <p className="text-body-sm text-ink-muted">{t.role}</p>
                  <a
                    href={t.linkedin}
                    target={t.linkedin === "#" ? undefined : "_blank"}
                    rel="noreferrer"
                    className="link-grow self-start pb-0.5 text-body-sm font-medium text-ink"
                  >
                    LinkedIn →
                  </a>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  );
}
