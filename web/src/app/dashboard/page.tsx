import { Suspense } from "react";
import { MainView } from "@/components/views/MainView";

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="sky-band min-h-dvh" />}>
      <MainView />
    </Suspense>
  );
}
