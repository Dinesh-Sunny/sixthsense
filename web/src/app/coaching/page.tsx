import { Suspense } from "react";
import { CoachingView } from "@/components/views/CoachingView";

export default function CoachingPage() {
  return (
    <Suspense fallback={<div className="sky-soft min-h-dvh" />}>
      <CoachingView />
    </Suspense>
  );
}
