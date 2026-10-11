const INK = "#2b2b28";

function Citizen() {
  return (
    <svg viewBox="0 0 240 160">
      <circle cx="120" cy="80" r="62" fill="#e9ed4c" opacity="0.35" />
      <circle cx="108" cy="56" r="20" fill="#fffdf6" stroke={INK} strokeWidth="2" />
      <path d="M70 132 C72 100 90 86 108 86 C126 86 144 100 146 132" fill="#fffdf6" stroke={INK} strokeWidth="2" />
      <path d="M100 52 Q108 46 116 52" fill="none" stroke={INK} strokeWidth="1.5" />
      <g transform="translate(146 66)">
        <rect width="64" height="40" rx="10" fill="#ffffff" stroke={INK} strokeWidth="2" />
        <path d="M8 22 H20 L25 12 L31 32 L36 22 H56" fill="none" stroke="#c2408f" strokeWidth="2" strokeLinejoin="round" />
      </g>
      <path d="M150 40 C150 33 159 31 162 37 C165 31 174 33 174 40 C174 48 162 55 162 55 C162 55 150 48 150 40 Z" fill="#c2408f" stroke={INK} strokeWidth="1.5" />
      <circle cx="56" cy="44" r="5" fill="#b9b8ae" />
      <circle cx="44" cy="62" r="3" fill="#b9b8ae" />
    </svg>
  );
}

function Worker() {
  return (
    <svg viewBox="0 0 240 160">
      <circle cx="120" cy="80" r="62" fill="#e8f0fa" />
      <g transform="translate(58 40)">
        <path d="M0 40 L30 16 L60 40" fill="#fffdf6" stroke={INK} strokeWidth="2" strokeLinejoin="round" />
        <rect x="6" y="40" width="48" height="40" fill="#fffdf6" stroke={INK} strokeWidth="2" />
        <path d="M26 52 H34 M30 48 V56" stroke="#c2408f" strokeWidth="3" strokeLinecap="round" />
        <rect x="24" y="64" width="12" height="16" fill="#e9ed4c" stroke={INK} strokeWidth="1.5" />
      </g>
      <g transform="translate(132 34)">
        <rect width="52" height="72" rx="6" fill="#ffffff" stroke={INK} strokeWidth="2" />
        <rect x="16" y="-6" width="20" height="12" rx="3" fill="#3a4fa0" />
        {[18, 34, 50].map((y) => (
          <g key={y}>
            <path d={`M8 ${y} l4 4 l7 -8`} fill="none" stroke="#62631e" strokeWidth="2" strokeLinecap="round" />
            <path d={`M24 ${y} H44`} stroke="#b9b8ae" strokeWidth="2" strokeLinecap="round" />
          </g>
        ))}
      </g>
      <path d="M118 126 C100 150 70 140 74 120 C76 110 88 110 90 118" fill="none" stroke="#3a4fa0" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="118" cy="126" r="6" fill="#fffdf6" stroke="#3a4fa0" strokeWidth="2.5" />
    </svg>
  );
}

function Admin() {
  return (
    <svg viewBox="0 0 240 160">
      <circle cx="120" cy="80" r="62" fill="#fbeef4" />
      {[0, 1, 2].map((i) => (
        <g key={i} transform={`translate(${44 + i * 10} ${54 + i * 12}) rotate(${-8 + i * 4})`}>
          <rect width="70" height="44" rx="6" fill="#ffffff" stroke={INK} strokeWidth="1.5" />
          <circle cx="16" cy="18" r="7" fill="#e4e3dc" />
          <path d="M30 14 H58 M30 24 H50" stroke="#b9b8ae" strokeWidth="2" strokeLinecap="round" />
        </g>
      ))}
      <path d="M156 34 L188 46 V74 C188 96 174 110 156 118 C138 110 124 96 124 74 V46 Z" fill="#e9ed4c" stroke={INK} strokeWidth="2" strokeLinejoin="round" />
      <path d="M142 76 L152 86 L172 64" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function RoleArt({ role }: { role: "citizen" | "worker" | "admin" }) {
  return (
    <div aria-hidden="true">
      {role === "citizen" ? <Citizen /> : role === "worker" ? <Worker /> : <Admin />}
    </div>
  );
}
