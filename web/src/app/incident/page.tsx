import { Suspense } from "react";
import { DetailView } from "@/components/views/DetailView";

export default function IncidentPage() {
  return (
    <Suspense fallback={<div className="sky-soft min-h-dvh" />}>
      <DetailView />
    </Suspense>
  );
}
