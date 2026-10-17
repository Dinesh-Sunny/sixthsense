import type { Metadata } from "next";
import { LandingView } from "@/components/views/LandingView";

export const metadata: Metadata = {
  title: "SixthSense · About",
  description: "Your cameras record everything. SixthSense tells you what happens next, then checks if it was right.",
};

export default function AboutPage() {
  return <LandingView />;
}
