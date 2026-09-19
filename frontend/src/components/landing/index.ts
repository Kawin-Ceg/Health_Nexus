import { lazy } from "react";

export { LandingNavbar } from "./LandingNavbar/LandingNavbar";
export { Hero } from "./Hero/Hero";
export { PhoneMockup } from "./PhoneMockup/PhoneMockup";
export { FeatureShowcase } from "./FeatureShowcase/FeatureShowcase";
export { CommunityShowcase } from "./CommunityShowcase/CommunityShowcase";
export { PrivacyBanner } from "./PrivacyBanner/PrivacyBanner";
export { FinalCta } from "./FinalCta/FinalCta";
export { Footer } from "./Footer/Footer";
export { Eyebrow } from "./Eyebrow/Eyebrow";

// Re-exported lazily: a static re-export would pull Recharts into the main chunk.
export const CommunityInsights = lazy(() => import("./CommunityInsights/CommunityInsights"));
