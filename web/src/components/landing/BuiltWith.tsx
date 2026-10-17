"use client";

import { Reveal, rise, stagger } from "@/components/landing/reveal";
import { assetUrl } from "@/lib/utils";

// Brand marks are the unmodified Simple Icons files (CC0 package, public/brands/), shown monochrome via
// CSS mask. Brands without a file stay as text wordmarks in our own type; no TfL roundel.
const BRANDS: { name: string; href: string; logo?: string }[] = [
  { name: "VAST Data", href: "https://www.vastdata.com/" },
  { name: "NVIDIA Cosmos", href: "https://www.nvidia.com/en-us/ai/cosmos/", logo: "nvidia" },
  { name: "CoreWeave", href: "https://www.coreweave.com/" },
  { name: "Ultralytics YOLO11", href: "https://docs.ultralytics.com/models/yolo11/", logo: "ultralytics" },
  { name: "Weights & Biases", href: "https://wandb.ai/site/", logo: "weightsandbiases" },
  { name: "Mapbox", href: "https://www.mapbox.com/", logo: "mapbox" },
  { name: "Socket.IO", href: "https://socket.io/", logo: "socketdotio" },
  { name: "TfL Open Data", href: "https://tfl.gov.uk/info-for/open-data-users/" },
];

function Mark({ logo }: { logo: string }) {
  const url = `url(${assetUrl(`/brands/${logo}.svg`)})`;
  return (
    <span
      aria-hidden
      className="inline-block size-5 shrink-0 bg-current"
      style={{ maskImage: url, WebkitMaskImage: url, maskSize: "contain", maskRepeat: "no-repeat", maskPosition: "center" }}
    />
  );
}

export function BuiltWith() {
  return (
    <section aria-labelledby="built-with-h" className="mx-auto max-w-[1200px] px-4 pt-16 md:px-10 md:pt-24 lg:px-[80px]">
      <Reveal className="flex flex-col items-center gap-5">
        <h2 id="built-with-h" className={`text-eye ${rise}`}>
          Built with
        </h2>
        <ul className="flex flex-wrap items-center justify-center gap-x-5 gap-y-3">
          {BRANDS.map((b, n) => (
            <li key={b.name} className={rise} style={stagger(n, 80)}>
              <a
                href={b.href}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-sm font-medium whitespace-nowrap text-ink-muted transition-colors duration-150 hover:text-ink"
              >
                {b.logo && <Mark logo={b.logo} />}
                {b.name}
              </a>
            </li>
          ))}
        </ul>
        <p className={`text-data text-ink-muted ${rise}`} style={stagger(BRANDS.length, 80)}>
          Logos are trademarks of their owners.
        </p>
      </Reveal>
    </section>
  );
}
