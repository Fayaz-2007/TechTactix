export default function TriNodeMark({ size = 24, color = "currentColor", loading = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      style={loading ? { animation: "spin-mark 1.1s linear infinite", transformOrigin: "24px 24px" } : undefined}
      aria-hidden="true"
    >
      <circle cx="24" cy="24" r="4" fill={color} />
      <line x1="24" y1="24" x2="24" y2="8" stroke={color} strokeWidth="4" strokeLinecap="round" />
      <circle cx="24" cy="8" r="4" fill={color} />
      <line x1="24" y1="24" x2="10.14" y2="32" stroke={color} strokeWidth="4" strokeLinecap="round" />
      <circle cx="10.14" cy="32" r="4" fill={color} />
      <line x1="24" y1="24" x2="37.86" y2="32" stroke={color} strokeWidth="4" strokeLinecap="round" />
      <circle cx="37.86" cy="32" r="4" fill={color} />
    </svg>
  );
}
