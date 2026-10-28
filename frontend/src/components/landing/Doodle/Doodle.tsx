import { useEffect, useId, useRef, type ReactNode } from "react";
import { BlurIn } from "../BlurIn/BlurIn";
import styles from "./Doodle.module.css";

export type Piece =
  | "beads"
  | "tissue"
  | "tree"
  | "ecg"
  | "honeycomb"
  | "radial"
  | "helix"
  | "capsules"
  | "network"
  | "botanical"
  | "flask"
  | "speckle"
  | "microbe"
  | "coral";

const BEADS = [
  [30, 40, 14], [62, 30, 11], [92, 46, 13], [70, 66, 10], [40, 78, 12], [104, 86, 9], [130, 60, 11], [150, 92, 8],
  [20, 108, 9], [86, 112, 12], [120, 130, 10], [56, 140, 8],
] as const;

const BRANCHES = [
  "M10 300 L70 250 L150 215 L230 160", "M70 250 L60 200 L40 170", "M60 200 L90 160", "M150 215 L130 170 L120 130",
  "M150 215 L200 280 L240 330", "M150 215 L250 250", "M230 160 L250 110", "M230 160 L280 140", "M200 280 L270 300",
] as const;
const TIPS = [[40, 170], [90, 160], [120, 130], [240, 330], [250, 250], [250, 110], [280, 140], [270, 300]] as const;

function Beads({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 170 160">
      <defs>
        <radialGradient id={id} cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#e4e3dc" />
          <stop offset="100%" stopColor="#e4e3dc" />
        </radialGradient>
      </defs>
      {BEADS.map(([x, y, r]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r={r} fill={`url(#${id})`} />
      ))}
    </svg>
  );
}

function Tissue({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 150 220">
      <defs>
        <pattern id={id} width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(18)">
          <circle cx="2" cy="2" r="1.3" fill="#c2408f" />
          <circle cx="6.5" cy="5" r="0.9" fill="#7b3fa6" />
          <circle cx="3.5" cy="7.5" r="0.6" fill="#e07fb0" />
        </pattern>
      </defs>
      <rect width="150" height="220" fill="#fbeef4" />
      <rect width="150" height="220" fill={`url(#${id})`} opacity="0.75" />
      <path d="M0 60 C40 40 80 90 150 70 M0 150 C50 120 90 180 150 160" stroke="#d15a99" strokeWidth="1.2" fill="none" opacity="0.6" />
    </svg>
  );
}

function Tree() {
  return (
    <svg viewBox="0 0 300 340">
      {BRANCHES.map((d) => (
        <path key={d} d={d} stroke="#3c3c38" strokeWidth="2" fill="none" strokeLinecap="round" />
      ))}
      {TIPS.map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="5" fill="#3c3c38" />
      ))}
    </svg>
  );
}

function Ecg({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 220 170">
      <defs>
        <pattern id={id} width="10" height="10" patternUnits="userSpaceOnUse">
          <path d="M10 0 L0 0 0 10" fill="none" stroke="#e7b9b0" strokeWidth="0.6" />
        </pattern>
      </defs>
      <rect width="220" height="170" fill="#fffdf6" stroke="#d9d6cb" />
      <rect x="10" y="14" width="200" height="120" fill={`url(#${id})`} />
      <path
        d="M10 84 H52 L58 78 L64 84 H74 L80 40 L88 120 L94 84 H118 L126 72 L134 84 H150 L156 46 L164 116 L170 84 H210"
        fill="none"
        stroke="#2b2b28"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <text x="12" y="154" fontFamily="Georgia, serif" fontSize="10" fill="#5a5a52" fontStyle="italic">
        Lead II · resting, 72 bpm
      </text>
    </svg>
  );
}

function Honeycomb({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 260 420">
      <defs>
        <pattern id={`${id}h`} width="30" height="26" patternUnits="userSpaceOnUse">
          <path d="M7.5 0 H22.5 L30 13 L22.5 26 H7.5 L0 13 Z" fill="none" stroke="#3a4fa0" strokeWidth="1.2" />
        </pattern>
        <clipPath id={`${id}c`}>
          <path d="M260 0 C120 40 60 160 70 260 C78 340 140 400 260 420 Z" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}c)`}>
        <rect width="260" height="420" fill={`url(#${id}h)`} opacity="0.85" />
      </g>
      <path d="M260 0 C120 40 60 160 70 260 C78 340 140 400 260 420" fill="none" stroke="#3a4fa0" strokeWidth="2.5" />
      <path d="M245 12 C110 60 52 170 60 262 C66 344 130 404 245 420" fill="none" stroke="#3a4fa0" strokeWidth="1" strokeDasharray="10 8" />
    </svg>
  );
}

function Radial() {
  return (
    <svg viewBox="0 0 360 160">
      {[60, 180, 300].map((cx) => (
        <g key={cx} transform={`translate(${cx} 90)`}>
          {Array.from({ length: 18 }, (_, i) => (
            <line key={i} x1="0" y1="0" x2="0" y2={i % 2 ? -38 : -52} transform={`rotate(${i * 20})`} stroke="#c9b98a" strokeWidth="1" />
          ))}
          <circle r="16" fill="#f3ead0" stroke="#c9b98a" />
          <circle r="4" fill="#c9b98a" />
        </g>
      ))}
    </svg>
  );
}

function Helix() {
  const rungs = Array.from({ length: 14 }, (_, i) => i * 22 + 10);
  return (
    <svg viewBox="0 0 120 320">
      <path d="M30 0 C90 40 90 80 30 120 C-30 160 -30 200 30 240 C90 280 90 300 60 320" fill="none" stroke="#62631e" strokeWidth="2" />
      <path d="M90 0 C30 40 30 80 90 120 C150 160 150 200 90 240 C30 280 30 300 60 320" fill="none" stroke="#3c3c38" strokeWidth="2" />
      {rungs.map((y) => (
        <line key={y} x1="30" x2="90" y1={y} y2={y} stroke="#9a9a8c" strokeWidth="1" strokeDasharray="3 3" />
      ))}
    </svg>
  );
}

function Capsules() {
  const pills = [
    { x: 20, y: 30, r: -30, a: "#e9ed4c", b: "#ffffff" },
    { x: 90, y: 70, r: 20, a: "#c2408f", b: "#fbeef4" },
    { x: 40, y: 120, r: 60, a: "#3a4fa0", b: "#e8f0fa" },
  ];
  return (
    <svg viewBox="0 0 170 180">
      {pills.map((p) => (
        <g key={`${p.x}-${p.y}`} transform={`translate(${p.x} ${p.y}) rotate(${p.r} 32 12)`}>
          <rect width="64" height="24" rx="12" fill={p.b} stroke="#3c3c38" strokeWidth="1.5" />
          <path d="M12 0 H32 V24 H12 A12 12 0 0 1 12 0 Z" fill={p.a} stroke="#3c3c38" strokeWidth="1.5" />
        </g>
      ))}
    </svg>
  );
}

const rand = (seed: number) => {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
};

const NET_NODES = Array.from({ length: 46 }, (_, i) => {
  const a = rand(i) * Math.PI * 2;
  const r = 40 + rand(i + 100) * 150;
  return [200 + Math.cos(a) * r * 1.1, 200 + Math.sin(a) * r] as const;
});
const NET_EDGES = NET_NODES.flatMap(([x, y], i) =>
  NET_NODES.slice(i + 1)
    .map(([x2, y2], j) => [i, i + 1 + j, Math.hypot(x2 - x, y2 - y)] as const)
    .filter(([, , d]) => d < 62)
    .map(([a, b]) => [a, b] as const),
);

function Network({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 400 400">
      <defs>
        <radialGradient id={id} cx="45%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#cdd8ea" />
          <stop offset="100%" stopColor="#cdd8ea" />
        </radialGradient>
      </defs>
      {NET_NODES.map(([x, y], i) => (
        <circle key={`b${i}`} cx={x} cy={y} r={14 + rand(i + 7) * 18} fill={`url(#${id})`} opacity="0.55" />
      ))}
      {NET_EDGES.map(([a, b]) => (
        <line key={`${a}-${b}`} x1={NET_NODES[a][0]} y1={NET_NODES[a][1]} x2={NET_NODES[b][0]} y2={NET_NODES[b][1]} stroke="#ffffff" strokeWidth="1" />
      ))}
      {NET_NODES.map(([x, y], i) => (
        <circle key={`n${i}`} cx={x} cy={y} r={i % 9 === 0 ? 4 : 2} fill={i % 9 === 0 ? "#e3a33b" : "#ffffff"} />
      ))}
    </svg>
  );
}

function Botanical() {
  const sprigs = [
    [60, 150, 30, 90],
    [90, 120, 120, 70],
    [140, 100, 190, 80],
    [170, 95, 210, 130],
    [110, 110, 95, 55],
  ] as const;
  return (
    <svg viewBox="0 0 240 240">
      <path d="M10 230 C60 170 120 120 220 70" fill="none" stroke="#9a9a8c" strokeWidth="1.2" />
      {sprigs.map(([x1, y1, x2, y2]) => (
        <g key={`${x1}-${y1}`}>
          <path d={`M${x1} ${y1} Q${(x1 + x2) / 2 + 6} ${(y1 + y2) / 2 - 6} ${x2} ${y2}`} fill="none" stroke="#a8a89a" strokeWidth="0.9" />
          {[0, 1, 2, 3].map((k) => (
            <circle key={k} cx={x2 + Math.cos(k * 1.6) * 7} cy={y2 + Math.sin(k * 1.6) * 7} r="1.8" fill="#9a9a8c" />
          ))}
        </g>
      ))}
    </svg>
  );
}

function Flask() {
  return (
    <svg viewBox="0 0 120 150">
      <path d="M45 10 H75 M50 10 V55 L18 125 C14 134 20 142 30 142 H90 C100 142 106 134 102 125 L70 55 V10" fill="none" stroke="#a8a89a" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M28 112 C48 104 72 120 92 110" fill="none" stroke="#9fb3d6" strokeWidth="1.2" />
      {[[40, 125], [60, 118], [76, 128]].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="2.5" fill="none" stroke="#9fb3d6" />
      ))}
    </svg>
  );
}

function Speckle() {
  return (
    <svg viewBox="0 0 160 140">
      {Array.from({ length: 240 }, (_, i) => {
        const a = rand(i + 300) * Math.PI * 2;
        const r = Math.sqrt(rand(i + 600)) * 60;
        const colors = ["#3a4fa0", "#c2408f", "#e3a33b", "#62631e", "#7a8fb8"];
        return <circle key={i} cx={80 + Math.cos(a) * r * 1.1} cy={70 + Math.sin(a) * r} r={0.8 + rand(i + 900) * 1.4} fill={colors[i % colors.length]} opacity="0.55" />;
      })}
    </svg>
  );
}

function Microbe() {
  return (
    <svg viewBox="0 0 260 220">
      <g transform="translate(120 100)">
        {Array.from({ length: 28 }, (_, i) => (
          <line key={i} x1="0" y1="-52" x2="0" y2={i % 2 ? -66 : -74} transform={`rotate(${i * (360 / 28)})`} stroke="#e07a3c" strokeWidth="1.6" />
        ))}
        <circle r="52" fill="#fdf1e8" stroke="#e07a3c" strokeWidth="2" />
        {Array.from({ length: 14 }, (_, i) => {
          const a = rand(i + 40) * Math.PI * 2;
          const r = 10 + rand(i + 80) * 32;
          return <rect key={i} x={Math.cos(a) * r - 4} y={Math.sin(a) * r - 4} width="8" height="8" rx="2" fill="none" stroke="#e07a3c" strokeWidth="1.2" transform={`rotate(${i * 25} ${Math.cos(a) * r} ${Math.sin(a) * r})`} />;
        })}
      </g>
      <path d="M180 60 L232 30 M70 150 L20 190 M190 150 L240 170" stroke="#5a5a52" strokeWidth="0.8" />
      {[[236, 28, "12"], [10, 200, "4"], [244, 176, "7"]].map(([x, y, n]) => (
        <text key={String(n)} x={Number(x)} y={Number(y)} fontFamily="Georgia, serif" fontSize="11" fontStyle="italic" fill="#5a5a52">
          {n}
        </text>
      ))}
    </svg>
  );
}

function Coral({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 240 260">
      <defs>
        <radialGradient id={id} cx="40%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#9b5cc7" />
          <stop offset="100%" stopColor="#9b5cc7" />
        </radialGradient>
      </defs>
      <path
        d="M120 20 C150 10 170 40 160 60 C190 50 220 80 200 105 C235 115 230 160 195 165 C215 195 185 225 155 205 C150 240 105 245 98 212 C70 235 35 210 52 180 C15 175 12 130 45 122 C20 95 45 60 78 72 C75 40 98 22 120 20 Z"
        fill={`url(#${id})`}
        stroke="#e9ed4c"
        strokeWidth="5"
        strokeLinejoin="round"
      />
      <path d="M110 70 C130 90 120 120 140 140 M80 130 C100 140 110 170 130 175" fill="none" stroke="#e9ed4c" strokeWidth="1.5" opacity="0.7" />
    </svg>
  );
}

function render(piece: Piece, id: string): ReactNode {
  switch (piece) {
    case "beads":
      return <Beads id={id} />;
    case "tissue":
      return <Tissue id={id} />;
    case "tree":
      return <Tree />;
    case "ecg":
      return <Ecg id={id} />;
    case "honeycomb":
      return <Honeycomb id={id} />;
    case "radial":
      return <Radial />;
    case "helix":
      return <Helix />;
    case "capsules":
      return <Capsules />;
    case "network":
      return <Network id={id} />;
    case "botanical":
      return <Botanical />;
    case "flask":
      return <Flask />;
    case "speckle":
      return <Speckle />;
    case "microbe":
      return <Microbe />;
    case "coral":
      return <Coral id={id} />;
  }
}

const live = new Set<HTMLDivElement>();
let frame = 0;
let pointer: { x: number; y: number } | null = null;

function update() {
  frame = 0;
  if (!pointer) return;
  for (const el of live) {
    if (el.dataset.ambient === "true") continue;
    const r = el.getBoundingClientRect();
    const over = !!r.width && pointer.x >= r.left && pointer.x <= r.right && pointer.y >= r.top && pointer.y <= r.bottom;
    if (over !== (el.dataset.hover === "true")) el.dataset.hover = String(over);
  }
}

function onPointer(event: PointerEvent) {
  if (event.pointerType === "touch") return;
  pointer = { x: event.clientX, y: event.clientY };
  if (!frame) frame = requestAnimationFrame(update);
}

function register(el: HTMLDivElement) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return () => undefined;
  if (live.size === 0) window.addEventListener("pointermove", onPointer, { passive: true });
  live.add(el);
  return () => {
    live.delete(el);
    if (live.size === 0) window.removeEventListener("pointermove", onPointer);
  };
}

export function Doodle({
  piece,
  className,
  delay = 0,
  ambient = false,
}: {
  piece: Piece;
  className?: string;
  delay?: 0 | 1 | 2 | 3 | 4;
  ambient?: boolean;
}) {
  const id = `doodle${useId().replace(/:/g, "")}`;
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => (ref.current ? register(ref.current) : undefined), []);
  return (
    <BlurIn delay={delay} className={[styles.doodle, className].filter(Boolean).join(" ")}>
      <div ref={ref} aria-hidden="true" data-piece={piece} data-ambient={ambient} className={styles.art}>
        {render(piece, id)}
      </div>
    </BlurIn>
  );
}
