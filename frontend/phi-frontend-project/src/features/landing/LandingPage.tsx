import { Hero } from "@/features/landing/components/Hero";
import { FeatureGrid } from "@/features/landing/components/FeatureGrid";
import { TechStackSection } from "@/features/landing/components/TechStackSection";
import { CtaSection } from "@/features/landing/components/CtaSection";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <FeatureGrid />
      <TechStackSection />
      <CtaSection />
    </>
  );
}
