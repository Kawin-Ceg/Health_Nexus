
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  ClipboardList,
  MapPin,
  MessageCircle,
  Stethoscope,
  TrendingUp,
  Users,
} from "lucide-react";

export type Icon = LucideIcon;

export interface NavLink {
  label: string;
  href: string;
}

export interface IconItem {
  icon: Icon;
  title: string;
  body: string;
}

export const brand = {
  name: "Health Nexus",
  homeLabel: "Health Nexus home",
  tagline: "Personal health tracking and community health intelligence, built with primary health centres.",
};

export const routes = {
  home: "/",
  login: "/login",
  signup: "/signup",
  phcSignup: "/signup/phc-worker",
  privacy: "/privacy-policy",
  terms: "/terms",
};

export const nav = {
  label: "Main",
  links: [
    { label: "Who it's for", href: "#roles" },
    { label: "Features", href: "#features" },
    { label: "Community", href: "#community" },
    { label: "Health insights", href: "#insights" },
    { label: "Privacy", href: "#privacy" },
  ] satisfies NavLink[],
  login: "Log in",
  getStarted: "Create account",
  openMenu: "Open menu",
  closeMenu: "Close menu",
  menuTitle: "Menu",
};

export const hero = {
  headingId: "hero-heading",
  heading: { lead: "Your health and your community's,", highlight: "in one place." },
  primaryCta: "Create account",
  secondaryCta: "I'm a PHC worker",
  trust: ["Free for citizens", "Explains, never diagnoses", "Your data stays yours"],
  chat: {
    label: "Example conversation with the Health Nexus assistant",
    source: "Example conversation",
    question: "My resting heart rate is 88 today. Is that normal for me?",
    answer:
      "That's higher than your usual resting rate, which has been about 72 bpm over your last 30 days. A single higher reading can happen with poor sleep, caffeine, stress or illness. If it stays above your usual range for several days, or you feel unwell, talk to your health centre.",
    reason: "Based on: your logged resting heart rate, last 30 days",
    disclaimer: "Health Nexus explains readings; it does not diagnose.",
  },
};

export const roles = {
  id: "roles",
  headingId: "roles-heading",
  eyebrow: "Who it's for",
  heading: "Pick where you start",
  body: "Health Nexus has one place for each person who uses it.",
  items: [
    {
      role: "citizen",
      who: "For citizens",
      title: "Look after your health",
      body: "Log your readings, see how they compare with your usual, and know a health worker is watching for unusual ones.",
      cta: "Create account",
      href: "/signup",
    },
    {
      role: "worker",
      who: "For PHC workers",
      title: "Look after your area",
      body: "Review flagged readings from your health centre, book visits and see which localities need attention.",
      cta: "Apply as a PHC worker",
      href: "/signup/phc-worker",
    },
    {
      role: "admin",
      who: "For administrators",
      title: "Keep it running safely",
      body: "Approve health workers, manage accounts and answer concerns. Admin accounts are set up for you.",
      cta: "Sign in",
      href: "/login",
    },
  ] as const,
};

export const features = {
  id: "features",
  headingId: "features-heading",
  eyebrow: "Features",
  heading: "What Health Nexus does",
  body: "Built for citizens and the health workers who look after them.",
  hub: { title: "Health Nexus", body: "You, your health centre and your community, connected.", hint: "Hover or tap to explore" },
  items: [
    {
      icon: Activity,
      title: "Track your readings",
      body: "Log blood pressure, heart rate, temperature, oxygen and more. Each reading is compared with your own usual, not a generic average.",
    },
    {
      icon: ClipboardList,
      title: "Your health record",
      body: "Readings, flags, visits and notifications in one place. Every flag shows which reading caused it.",
    },
    {
      icon: MapPin,
      title: "Your health centre",
      body: "See the primary health centre that covers your area, and get notified when its health worker books a visit with you.",
    },
    {
      icon: Users,
      title: "Community signals",
      body: "Health workers see how many people in each locality have unusual readings, without anyone being named.",
    },
    {
      icon: MessageCircle,
      title: "Plain-language explanations",
      body: "Ask about your readings in plain words. It explains; it doesn't diagnose.",
    },
    {
      icon: Stethoscope,
      title: "Health worker tools",
      body: "A worklist of flagged citizens, visit scheduling and a locality risk map for each health centre.",
    },
  ] satisfies IconItem[],
};

export const community = {
  id: "community",
  headingId: "community-heading",
  eyebrow: "For PHC workers",
  heading: "How community signals work",
  body: "When several people in one locality show unusual readings, the health worker for that area can see it early. Signals use grouped readings; no individual is named.",
  exampleCaption: "Example: how a health worker sees localities (illustrative, not real data)",
  exampleColumns: { area: "Area", citizens: "Citizens", flagged: "With an unusual reading", status: "Status" },
  exampleRows: [
    { area: "Area A", citizens: 42, flagged: 9, status: "Above usual, under review" },
    { area: "Area B", citizens: 35, flagged: 2, status: "Typical" },
    { area: "Area C", citizens: 28, flagged: 1, status: "Typical" },
    { area: "Area D", citizens: 19, flagged: 0, status: "Typical" },
  ],
  points: [
    {
      icon: Activity,
      title: "Locality view",
      body: "Each locality shows the share of its citizens with an open flag. Localities with fewer than three people are merged so nobody can be identified.",
    },
    {
      icon: TrendingUp,
      title: "Trend analysis",
      body: "Week-on-week counts show whether a local rise is growing or settling.",
    },
  ] satisfies IconItem[],
};

export type ChartRow = { period: string; normal: number; elevated: number; high: number };

export const insights = {
  id: "insights",
  headingId: "insights-heading",
  eyebrow: "Health insights",
  heading: "Community health at a glance",
  body: "Each reading is grouped by how far it is from that person's own usual range: within it, somewhat above, or well above.",
  chartTitle: "Readings by distance from each person's usual range, 8 weeks",
  chartSummary:
    "Stacked bars for eight weeks. Readings within the usual range stay steady around 900 a week, while readings above it rise in weeks 6 and 7 and ease in week 8.",
  illustrative: "Illustrative example, not real data",
  periodNote: "W1 is 8 weeks ago; W8 is this week.",
  tableToggle: "Show data table",
  tableColumns: { period: "Week", total: "Total" },
  legend: {
    normal: "Within usual range",
    elevated: "Somewhat above",
    high: "Well above",
  },
  tooltipTotal: "Total",
  data: [
    { period: "W1", normal: 912, elevated: 118, high: 21 },
    { period: "W2", normal: 947, elevated: 109, high: 18 },
    { period: "W3", normal: 889, elevated: 126, high: 24 },
    { period: "W4", normal: 931, elevated: 131, high: 27 },
    { period: "W5", normal: 904, elevated: 142, high: 33 },
    { period: "W6", normal: 876, elevated: 187, high: 52 },
    { period: "W7", normal: 858, elevated: 203, high: 61 },
    { period: "W8", normal: 921, elevated: 164, high: 39 },
  ] satisfies ChartRow[],
  stats: {
    thisWeek: "Example readings this week",
    aboveUsual: "Example readings above usual this week",
    areas: { value: "4", label: "Example areas" },
  },
};

export const privacy = {
  id: "privacy",
  headingId: "privacy-heading",
  eyebrow: "Privacy & trust",
  heading: "Your data stays yours",
  points: [
    "Community views only use grouped counts. Localities with fewer than three people are merged so nobody can be picked out.",
    "Health workers see your details only if you are registered at their health centre.",
    "You can download all your data, delete any reading, change your consent choices, or deactivate your account from Settings.",
    "Passwords and sign-in tokens are stored only as one-way hashes.",
  ],
  link: "Read our privacy policy",
};

export const finalCta = {
  headingId: "final-cta-heading",
  eyebrow: "Get started",
  heading: { lead: "Start looking after your health,", rest: "and your community's, today" },
  body: "Free for citizens. Create an account, confirm your email, and set up your health profile.",
  cta: "Create account",
  secondaryCta: "I'm a PHC worker",
  note: "No ads. Download your data or delete any reading, any time.",
};

export const footer = {
  label: "Footer",
  statement: "It explains; it doesn't diagnose.",
  emergency: "In an emergency, call 108.",
  columns: [
    {
      title: "Platform",
      links: [
        { label: "Features", href: "#features" },
        { label: "Health insights", href: "#insights" },
        { label: "Community", href: "#community" },
        { label: "Privacy & Trust", href: "#privacy" },
      ],
    },
    {
      title: "Account",
      links: [
        { label: "Create account", href: routes.signup },
        { label: "PHC worker signup", href: routes.phcSignup },
        { label: "Log in", href: routes.login },
      ],
    },
  ] satisfies { title: string; links: NavLink[] }[],
  legalLabel: "Legal",
  legal: [
    { label: "Privacy policy", href: routes.privacy },
    { label: "Terms of service", href: routes.terms },
  ] satisfies NavLink[],
  copyright: `© ${new Date().getFullYear()} Health Nexus`,
};

export const chartFallbackLabel = "Loading community insights";
