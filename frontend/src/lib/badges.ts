export const BADGES_EVENT = "hn:badges";
export const refreshBadges = () => window.dispatchEvent(new Event(BADGES_EVENT));
