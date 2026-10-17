import { Suspense } from "react";
import { ReportsView } from "@/components/views/ReportsView";

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="sky-band min-h-dvh" />}>
      <ReportsView />
    </Suspense>
  );
}
