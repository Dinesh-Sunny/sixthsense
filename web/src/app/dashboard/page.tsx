import { Suspense } from "react";
import { LiveMapView } from "@/components/views/LiveMapView";

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="sky-soft min-h-dvh" />}>
      <LiveMapView />
    </Suspense>
  );
}
