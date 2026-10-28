import { lazy } from "react";

export { LandingNavbar } from "./LandingNavbar/LandingNavbar";
export { Hero } from "./Hero/Hero";
export { Roles } from "./Roles/Roles";
export { FeatureShowcase } from "./FeatureShowcase/FeatureShowcase";
export { PrivacyBanner } from "./PrivacyBanner/PrivacyBanner";
export { FinalCta } from "./FinalCta/FinalCta";
export { Footer } from "./Footer/Footer";
export { Eyebrow } from "./Eyebrow/Eyebrow";

export const CommunityInsights = lazy(() => import("./CommunityInsights/CommunityInsights"));
