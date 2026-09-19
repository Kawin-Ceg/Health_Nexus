import { Suspense } from "react";
import { chartFallbackLabel, insights } from "../content/landing";
import {
  CommunityInsights,
  CommunityShowcase,
  FeatureShowcase,
  FinalCta,
  Footer,
  Hero,
  LandingNavbar,
  PrivacyBanner,
} from "../components/landing";
import { LazySection } from "../components/ui/LazySection/LazySection";
import styles from "./LandingPage.module.css";

/**
 * Fixed-height placeholder so the page does not shift when the chart chunk
 * loads. It carries the section's anchor id so "#insights" links still land.
 */
function ChartSectionFallback() {
  return (
    <div id={insights.id} className={styles.chartFallback} role="status">
      <span className="visually-hidden">{chartFallbackLabel}</span>
    </div>
  );
}

export function LandingPage() {
  return (
    <>
      <LandingNavbar />
      <main>
        <Hero />
        <FeatureShowcase />
        <CommunityShowcase />
        <LazySection placeholder={<ChartSectionFallback />}>
          <Suspense fallback={<ChartSectionFallback />}>
            <CommunityInsights />
          </Suspense>
        </LazySection>
        <PrivacyBanner />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
