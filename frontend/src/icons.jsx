// Lucide-style inline SVG icons (zero dependencies)
const base = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round',
}

export const Logo = (p) => (
  <svg {...base} {...p} viewBox="0 0 24 24">
    <path d="M3 3v18h18" />
    <rect x="7" y="12" width="3" height="6" rx="1" fill="currentColor" stroke="none" />
    <rect x="12" y="8" width="3" height="10" rx="1" fill="currentColor" stroke="none" opacity="0.7" />
    <rect x="17" y="4" width="3" height="14" rx="1" fill="currentColor" stroke="none" opacity="0.45" />
  </svg>
)

export const Sparkles = (p) => (
  <svg {...base} {...p}>
    <path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" />
    <path d="M19 14l.9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9z" />
  </svg>
)

export const FileIcon = (p) => (
  <svg {...base} {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
  </svg>
)

export const Search = (p) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.3-4.3" />
  </svg>
)

export const Send = (p) => (
  <svg {...base} {...p}>
    <path d="M22 2L11 13" />
    <path d="M22 2l-7 20-4-9-9-4z" />
  </svg>
)

export const Paperclip = (p) => (
  <svg {...base} {...p}>
    <path d="M21.4 11.05l-9.19 9.19a5 5 0 0 1-7.07-7.07l9.19-9.19a3 3 0 0 1 4.24 4.24l-9.2 9.19a1 1 0 0 1-1.41-1.41l8.49-8.49" />
  </svg>
)

export const Check = (p) => (
  <svg {...base} {...p}><path d="M20 6L9 17l-5-5" /></svg>
)

export const X = (p) => (
  <svg {...base} {...p}><path d="M18 6L6 18M6 6l12 12" /></svg>
)

export const Rows = (p) => (
  <svg {...base} {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M3 10h18M3 14h18" />
  </svg>
)

export const Columns = (p) => (
  <svg {...base} {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M9 5v14M15 5v14" />
  </svg>
)

export const AlertDot = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v4M12 16h.01" />
  </svg>
)

export const Activity = (p) => (
  <svg {...base} {...p}><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
)

export const Layers = (p) => (
  <svg {...base} {...p}>
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
  </svg>
)

export const Copy = (p) => (
  <svg {...base} {...p}>
    <rect x="9" y="9" width="13" height="13" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
)

export const Code = (p) => (
  <svg {...base} {...p}><path d="M16 18l6-6-6-6M8 6l-6 6 6 6" /></svg>
)

export const ChartUp = (p) => (
  <svg {...base} {...p}>
    <path d="M3 3v18h18" />
    <path d="M19 9l-5 5-4-4-3 3" />
  </svg>
)

export const Brain = (p) => (
  <svg {...base} {...p}>
    <path d="M12 5a3 3 0 0 0-5.9-.7A2.5 2.5 0 0 0 4 9a2.5 2.5 0 0 0 .5 4.9A3 3 0 0 0 7 19a3 3 0 0 0 5 1 3 3 0 0 0 5-1 3 3 0 0 0 2.5-5.1A2.5 2.5 0 0 0 20 9a2.5 2.5 0 0 0-2.1-4.7A3 3 0 0 0 12 5z" />
    <path d="M12 5v15" />
  </svg>
)

export const DollarSign = (p) => (
  <svg {...base} {...p}>
    <path d="M12 1v22" />
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </svg>
)

export const HeartPulse = (p) => (
  <svg {...base} {...p}>
    <path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3 5.5 5.5 0 0 0 12 5.4 5.5 5.5 0 0 0 7.5 3 5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z" />
    <path d="M3.2 12H8l1.5-3 3 6 1.5-3h3.8" />
  </svg>
)

export const ShoppingCart = (p) => (
  <svg {...base} {...p}>
    <circle cx="9" cy="21" r="1.5" />
    <circle cx="19" cy="21" r="1.5" />
    <path d="M2 3h2.5l2.2 12.4a2 2 0 0 0 2 1.6h8.7a2 2 0 0 0 2-1.6L23 7H6" />
  </svg>
)

export const Megaphone = (p) => (
  <svg {...base} {...p}>
    <path d="M3 11v2a1 1 0 0 0 1 1h2l4 4V6L6 10H4a1 1 0 0 0-1 1z" />
    <path d="M14 7.5a5 5 0 0 1 0 9" />
  </svg>
)

export const Users = (p) => (
  <svg {...base} {...p}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11" />
  </svg>
)

export const Zap = (p) => (
  <svg {...base} {...p}>
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
)

export const Terminal = (p) => (
  <svg {...base} {...p}>
    <polyline points="4 17 10 11 4 5" />
    <line x1="12" y1="19" x2="20" y2="19" />
  </svg>
)

export const Lock = (p) => (
  <svg {...base} {...p}>
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

export const Award = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="8" r="7" />
    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
  </svg>
)

export const Eye = (p) => (
  <svg {...base} {...p}>
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
)

export const Download = (p) => (
  <svg {...base} {...p}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

export const FileText = (p) => (
  <svg {...base} {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
)

export const Sliders = (p) => (
  <svg {...base} {...p}>
    <line x1="4" y1="21" x2="4" y2="14" />
    <line x1="4" y1="10" x2="4" y2="3" />
    <line x1="12" y1="21" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12" y2="3" />
    <line x1="20" y1="21" x2="20" y2="16" />
    <line x1="20" y1="12" x2="20" y2="3" />
    <line x1="1" y1="14" x2="7" y2="14" />
    <line x1="9" y1="8" x2="15" y2="8" />
    <line x1="17" y1="16" x2="23" y2="16" />
  </svg>
)

export const SlidersHorizontal = Sliders

export const TrendingUp = (p) => (
  <svg {...base} {...p}>
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
)

