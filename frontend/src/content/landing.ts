/* All landing-page copy. Components read from here and hold no text of their own.
   Headings are split so the emphasis word can be set in italic serif. */

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BellRing,
  ClipboardList,
  Droplet,
  Footprints,
  HandHeart,
  HeartPulse,
  Hospital,
  MapPin,
  MessageCircle,
  Moon,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";

export type Icon = LucideIcon;

export interface Heading {
  lead: string;
  emphasis: string;
  tail: string;
}

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
  name: "HealthNexus",
  homeLabel: "HealthNexus home",
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
    { label: "Features", href: "#features" },
    { label: "Community", href: "#community" },
    { label: "Health Insights", href: "#insights" },
    { label: "Privacy", href: "#privacy" },
  ] satisfies NavLink[],
  login: "Log in",
  getStarted: "Get started",
  openMenu: "Open menu",
  closeMenu: "Close menu",
  menuTitle: "Menu",
};

export const hero = {
  headingId: "hero-heading",
  eyebrow: "Health surveillance for everyone",
  heading: { lead: "Your health, and your community's, in ", emphasis: "one", tail: " place." } satisfies Heading,
  body: "Log your vitals, spot changes early, and help local health workers see outbreaks before they spread.",
  primaryCta: "Create account",
  secondaryCta: "I'm a PHC worker",
  chat: {
    label: "Example: HealthNexus explaining a smartwatch reading",
    source: "From your smartwatch, synced 7:40 am",
    question: "My watch says my resting heart rate is 88 today. Is that normal for me?",
    typing: "HealthNexus is typing",
    answer:
      "It's higher than your usual 72 bpm. It started rising after three nights of short sleep. If it stays high for two more days, we'll let your PHC know.",
    reason: "Driven by: resting heart rate",
  },
  pillarsLabel: "What HealthNexus covers",
  pillars: [
    { icon: HeartPulse, title: "Personal Health", body: "Track vitals against your own normal, not a generic average." },
    { icon: Hospital, title: "Healthcare Access", body: "Find your nearest PHC and book a visit when you need one." },
    { icon: Users, title: "Community Intelligence", body: "Anonymous signals show what is going around your area." },
    { icon: ShieldCheck, title: "Secure & Private", body: "Your records stay yours. You choose who can see them." },
  ] satisfies IconItem[],
};

export const phone = {
  greeting: "Good morning",
  date: "Today",
  status: "All vitals in your usual range",
  tiles: [
    { icon: HeartPulse, label: "Heart Rate", value: "72", unit: "bpm", tone: "brand" },
    { icon: Moon, label: "Sleep", value: "7h 20m", unit: "", tone: "neutral" },
    { icon: Footprints, label: "Steps", value: "6,418", unit: "", tone: "neutral" },
    { icon: Droplet, label: "SpO₂", value: "98", unit: "%", tone: "accent" },
  ] as const,
};

export const features = {
  id: "features",
  headingId: "features-heading",
  eyebrow: "Features",
  heading: { lead: "Everything you need to ", emphasis: "stay", tail: " ahead of your health." } satisfies Heading,
  body: "Built for citizens, and for the health workers who look after them.",
  items: [
    {
      icon: Activity,
      title: "Personal Health Tracking",
      body: "Log your vitals and see how today compares with your usual.",
    },
    {
      icon: ClipboardList,
      title: "Unified Health Record",
      body: "Readings, visits and reminders in one place.",
    },
    {
      icon: MapPin,
      title: "Find Healthcare Nearby",
      body: "See the health centre that covers your area.",
    },
    {
      icon: Users,
      title: "Community Intelligence",
      body: "Spot illness spreading nearby, without naming anyone.",
    },
    {
      icon: MessageCircle,
      title: "AI Health Assistant",
      body: "Ask about your readings in plain words. It explains; it doesn't diagnose.",
    },
  ] satisfies IconItem[],
};

export const community = {
  id: "community",
  headingId: "community-heading",
  eyebrow: "Community",
  heading: { lead: "See what's happening ", emphasis: "around", tail: " you." } satisfies Heading,
  body: "When many people nearby show the same change, local health workers hear about it early.",
  live: "Live",
  liveLabel: "Community signals are updated as readings come in",
  mapCaption: "Signals grouped by locality",
  localities: ["Mylapore", "Adyar", "Ambattur", "Tambaram"],
  points: [
    {
      icon: Activity,
      title: "Disease Surveillance",
      body: "Unusual readings that cluster in time and place are flagged to the nearest PHC.",
    },
    {
      icon: TrendingUp,
      title: "Trend Analysis",
      body: "Week-on-week patterns show whether a local rise is growing or settling.",
    },
    {
      icon: HandHeart,
      title: "Community Impact",
      body: "Every reading you log helps protect the people who live near you.",
    },
  ] satisfies IconItem[],
};

export type ChartRow = { period: string; normal: number; elevated: number; high: number };

export const insights = {
  id: "insights",
  headingId: "insights-heading",
  eyebrow: "Health Insights",
  heading: { lead: "Community health, ", emphasis: "at a glance", tail: "." } satisfies Heading,
  body: "Anonymous readings from a sample district, grouped by severity each week.",
  chartTitle: "Anonymous readings by severity, last 8 weeks",
  chartSummary:
    "Stacked bars for eight weeks. Normal readings stay steady around 900 a week, while elevated and high readings rise in weeks 6 and 7 and ease in week 8.",
  illustrative: "Illustrative sample data",
  legend: {
    normal: "Normal",
    elevated: "Elevated",
    high: "High",
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
  stats: [
    { value: "1,124", label: "Anonymous reports this week" },
    { value: "14", label: "Regions monitored" },
    { value: "3", label: "Active community alerts" },
  ],
};

export const privacy = {
  id: "privacy",
  headingId: "privacy-heading",
  eyebrow: "Privacy & Trust",
  heading: { lead: "Your data is ", emphasis: "yours", tail: ". Always." } satisfies Heading,
  body: "Community insights only ever use anonymous, grouped readings. Health workers see your details only inside their own catchment, and you can export or delete your records at any time.",
  link: "Read our privacy policy",
};

export const finalCta = {
  headingId: "final-cta-heading",
  eyebrow: "Get started",
  heading: { lead: "Start looking after your health ", emphasis: "today", tail: "." } satisfies Heading,
  body: "Free for citizens. Setup takes about two minutes.",
  cta: "Create account",
  benefitsLabel: "Why people join",
  benefits: [
    { icon: ShieldCheck, title: "Secure & Private", body: "Encrypted records you control." },
    { icon: Sparkles, title: "AI-Powered Insights", body: "Every flag shows which vital caused it." },
    { icon: Users, title: "Community Driven", body: "Your readings help people nearby." },
    { icon: BellRing, title: "Smart Reminders", body: "Nudges for readings and visits." },
  ] satisfies IconItem[],
};

export const footer = {
  label: "Footer",
  columns: [
    {
      title: "Platform",
      links: [
        { label: "Features", href: "#features" },
        { label: "Health Insights", href: "#insights" },
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
  newsletter: {
    title: "Health updates, monthly",
    body: "Community health news for your district. No spam.",
    label: "Email address",
    placeholder: "you@example.com",
    submit: "Subscribe",
    success: "Thanks. Check your inbox to confirm.",
    invalid: "Enter a valid email address.",
  },
  legalLabel: "Legal",
  legal: [
    { label: "Privacy policy", href: routes.privacy },
    { label: "Terms", href: routes.terms },
  ] satisfies NavLink[],
  copyright: `© ${new Date().getFullYear()} HealthNexus`,
};

export const chartFallbackLabel = "Loading community insights";
