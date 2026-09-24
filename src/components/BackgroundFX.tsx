export function BackgroundFX() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-40" />
      <div className="absolute -top-40 -left-40 h-[520px] w-[520px] rounded-full bg-emerald/30 blur-[140px] animate-drift" />
      <div className="absolute top-1/3 -right-40 h-[500px] w-[500px] rounded-full bg-cyan-glow/20 blur-[140px] animate-drift" style={{ animationDelay: "-4s" }} />
      <div className="absolute bottom-0 left-1/2 h-[400px] w-[400px] -translate-x-1/2 rounded-full bg-emerald/25 blur-[120px] animate-drift" style={{ animationDelay: "-8s" }} />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background/80" />
    </div>
  );
}
