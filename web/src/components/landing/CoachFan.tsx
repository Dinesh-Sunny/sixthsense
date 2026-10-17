"use client";

import { useInView } from "@/components/landing/reveal";
import { assetUrl } from "@/lib/utils";

// Real archive frames as clip thumbnails; the card is an illustration of a coaching card, no numbers.
const THUMBS = [
  { src: "/landing/f1.jpg", rot: -9, x: -46 },
  { src: "/landing/f5.jpg", rot: 0, x: 0 },
  { src: "/landing/f2.jpg", rot: 9, x: 46 },
];

export function CoachFan() {
  const [ref, inView] = useInView<HTMLDivElement>(0.4);
  return (
    <div ref={ref} className="relative mt-2 h-[108px]" aria-hidden>
      {THUMBS.map((t, n) => (
        <img
          key={t.src}
          src={assetUrl(t.src)}
          alt=""
          className="absolute top-2 left-1/2 aspect-video w-[120px] rounded-[10px] border-2 border-surface object-cover shadow-float transition-transform duration-[650ms] ease-out"
          style={{
            transform: inView
              ? `translate(calc(-50% + ${t.x}px), 0) rotate(${t.rot}deg)`
              : "translate(-50%, 10px) rotate(0deg)",
            transitionDelay: `${n * 100}ms`,
            zIndex: n === 1 ? 2 : 1,
          }}
        />
      ))}
    </div>
  );
}
