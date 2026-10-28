import { Suspense } from "react";
import { chartFallbackLabel, insights } from "../content/landing";
import {
  CommunityInsights,
  FeatureShowcase,
  FinalCta,
  Footer,
  Hero,
  Roles,
  LandingNavbar,
  PrivacyBanner,
} from "../components/landing";
import { LazySection } from "../components/ui/LazySection/LazySection";
import styles from "./LandingPage.module.css";

function ChartSectionFallback() {
  return (
    <div id={insights.id} className={styles.chartFallback} role="status">
      <span className="visually-hidden">{chartFallbackLabel}</span>
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="landing">
      <LandingNavbar />
      <main>
        <Hero />
        <Roles />
        <FeatureShowcase />
        <LazySection placeholder={<ChartSectionFallback />}>
          <Suspense fallback={<ChartSectionFallback />}>
            <CommunityInsights />
          </Suspense>
        </LazySection>
        <PrivacyBanner />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
