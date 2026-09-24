import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { Link } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Upload,
  GitCompare,
  Cpu,
  Dna as DnaIcon,
  LineChart as LineChartIcon,
  BookOpen,
  Settings,
  Bell,
  Search,
  User,
  Sun,
  Moon,
  ArrowUpRight,
  Zap,
  Activity,
  Timer,
  Database,
  ChevronRight,
  FileText,
  Play,
  type LucideIcon,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  RadialBar,
  RadialBarChart,
} from "recharts";
import { BackgroundFX } from "@/components/BackgroundFX";
import { DNAHelix } from "@/components/DNAHelix";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16, filter: "blur(6px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  },
};
const stagger: Variants = { show: { transition: { staggerChildren: 0.06 } } };

const sidebarItems = [
  { icon: LayoutDashboard, label: "Dashboard", id: "overview" },
  { icon: Upload, label: "DNA Upload", id: "upload" },
  { icon: GitCompare, label: "Sequence Alignment", id: "alignment" },
  { icon: Cpu, label: "Quantum Circuit", id: "circuit" },
  { icon: DnaIcon, label: "Visualization", id: "viz" },
  { icon: LineChartIcon, label: "Analytics", id: "analytics" },
  { icon: BookOpen, label: "Research Papers", id: "papers" },
  { icon: Settings, label: "Settings", id: "settings" },
];

const alignmentSeries = Array.from({ length: 24 }, (_, i) => ({
  x: i,
  score: 60 + Math.sin(i / 2) * 15 + Math.random() * 10,
  classical: 40 + Math.random() * 20,
}));
const mutationData = Array.from({ length: 12 }, (_, i) => ({
  name: `chr${i + 1}`,
  freq: Math.round(20 + Math.random() * 80),
}));
const baseDist = [
  { name: "A", value: 32, color: "#10B981" },
  { name: "T", value: 28, color: "#ef4444" },
  { name: "G", value: 22, color: "#eab308" },
  { name: "C", value: 18, color: "#38bdf8" },
];
const speedupData = [{ name: "Speedup", value: 78, fill: "#10B981" }];

const REFERENCE = "ATGCGTACGTTAGCTAGCTAGCTTAGCGGCTAAGCTGACGATCGTAAGCTAGGCTAGCGA";
const QUERY = "ATGCGTACCTTAGCTAG-TAGCTTAGCGGCTAAGCTGACGGTCGTAAGCTATGCTAGCGA";

const BASE_COLOR: Record<string, string> = {
  A: "text-emerald",
  T: "text-red-400",
  G: "text-yellow-400",
  C: "text-cyan-400",
};

export function Dashboard() {
  const [active, setActive] = useState("overview");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="relative min-h-screen">
      <BackgroundFX />
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-white/5 backdrop-blur-xl bg-sidebar/80 transition-all ${collapsed ? "w-16" : "w-64"}`}
      >
        <div className="flex h-16 items-center gap-2 border-b border-white/5 px-4">
          <div className="relative h-8 w-8 rounded-lg bg-gradient-to-br from-emerald to-cyan-glow glow-emerald flex items-center justify-center">
            <DnaIcon className="h-4 w-4 text-background" />
          </div>
          {!collapsed && <div className="font-display text-lg font-semibold">QDNA</div>}
        </div>
        <nav className="flex-1 space-y-1 p-3">
          <Link to="/qml" className="group flex w-full items-center gap-3 rounded-lg border border-emerald/20 bg-emerald/10 px-3 py-2 text-sm font-medium text-emerald transition hover:bg-emerald/20"><Activity className="h-4 w-4 shrink-0" />{!collapsed && <span>QML Clinical Lab</span>}</Link>
          {sidebarItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActive(item.id)}
              className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                active === item.id
                  ? "bg-emerald/15 text-emerald border border-emerald/30"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && active === item.id && <ChevronRight className="ml-auto h-3.5 w-3.5" />}
            </button>
          ))}
        </nav>
        <div className="border-t border-white/5 p-3">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full rounded-lg px-3 py-2 text-xs text-muted-foreground hover:bg-white/5"
          >
            {collapsed ? "→" : "← Collapse"}
          </button>
        </div>
      </aside>

      <div className={`${collapsed ? "pl-16" : "pl-64"} transition-all`}>
        {/* Topbar */}
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-white/5 bg-background/50 backdrop-blur-xl px-6">
          <Link to="/" className="text-xs text-muted-foreground hover:text-foreground">
            ← Home
          </Link>
          <div className="relative ml-4 flex-1 max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              placeholder="Search sequences, gates, papers…"
              className="w-full rounded-full border border-white/10 bg-white/5 py-2 pl-10 pr-3 text-sm placeholder:text-muted-foreground focus:border-emerald/40 focus:outline-none focus:ring-2 focus:ring-emerald/20"
            />
          </div>
          <button className="rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground">
            <Sun className="h-4 w-4" />
          </button>
          <button className="relative rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground">
            <Bell className="h-4 w-4" />
            <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-emerald" />
          </button>
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-3">
            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-emerald to-cyan-glow" />
            <div className="text-xs">
              <div className="font-medium">Dr. Nova</div>
              <div className="text-muted-foreground">Researcher</div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1400px] space-y-8 p-6 lg:p-8">
          {/* Header */}
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="show"
            className="flex flex-wrap items-end justify-between gap-4"
          >
            <motion.div variants={fadeUp}>
              <div className="text-xs uppercase tracking-widest text-emerald">Workspace</div>
              <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">
                Quantum Alignment Lab
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Live simulation · <span className="text-emerald">12 qubits</span> · connected to
                Grover oracle v2.4
              </p>
            </motion.div>
            <motion.div variants={fadeUp} className="flex items-center gap-2">
              <button className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10">
                <FileText className="h-4 w-4" /> Export
              </button>
              <button className="inline-flex items-center gap-2 rounded-full bg-emerald px-4 py-2 text-sm font-semibold text-primary-foreground glow-emerald">
                <Play className="h-4 w-4" /> Run Alignment
              </button>
            </motion.div>
          </motion.div>

          {/* Stat cards */}
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="show"
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            <StatCard
              icon={Database}
              label="Uploaded Sequences"
              value="1,284"
              delta="+12.4%"
              data={alignmentSeries.map((d) => ({ v: d.score }))}
            />
            <StatCard
              icon={Cpu}
              label="Quantum Circuits"
              value="342"
              delta="+8.1%"
              data={alignmentSeries.map((d) => ({ v: d.classical }))}
            />
            <StatCard
              icon={Activity}
              label="Alignment Accuracy"
              value="98.6%"
              delta="+2.3%"
              data={alignmentSeries.map((d) => ({ v: d.score * 1.1 }))}
            />
            <StatCard
              icon={Timer}
              label="Avg Execution"
              value="1.42s"
              delta="-31%"
              positive={false}
              data={alignmentSeries.map((d) => ({ v: 100 - d.classical }))}
            />
          </motion.div>

          {/* Main grid */}
          <div className="grid gap-4 lg:grid-cols-3">
            {/* DNA Visualization */}
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="glass relative overflow-hidden rounded-2xl p-5 lg:col-span-2 h-[420px]"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-widest text-emerald">
                    DNA Visualization
                  </div>
                  <div className="mt-1 font-display text-xl font-semibold">Live Double Helix</div>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <LegendDot color="#10B981" label="A" />
                  <LegendDot color="#ef4444" label="T" />
                  <LegendDot color="#eab308" label="G" />
                  <LegendDot color="#38bdf8" label="C" />
                </div>
              </div>
              <div className="absolute inset-0 top-16">
                <DNAHelix className="h-full w-full" />
              </div>
            </motion.div>

            {/* Sequence upload */}
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="glass rounded-2xl p-5"
            >
              <div className="text-xs uppercase tracking-widest text-emerald">Sequence Input</div>
              <div className="mt-1 font-display text-xl font-semibold">Upload DNA</div>
              <div className="mt-4 flex h-32 flex-col items-center justify-center rounded-xl border border-dashed border-emerald/30 bg-emerald/5 text-center transition hover:border-emerald hover:bg-emerald/10">
                <Upload className="h-6 w-6 text-emerald" />
                <div className="mt-2 text-sm font-medium">Drop FASTA / TXT here</div>
                <div className="text-xs text-muted-foreground">or paste sequence below</div>
              </div>
              <textarea
                placeholder=">seq1\nATGCGTACGT..."
                className="mt-3 h-24 w-full resize-none rounded-lg border border-white/10 bg-black/30 p-3 font-mono text-xs placeholder:text-muted-foreground focus:border-emerald/40 focus:outline-none"
              />
              <div className="mt-3 flex items-center justify-between">
                <div className="text-xs text-muted-foreground">FASTA · TXT · manual</div>
                <button className="rounded-full bg-emerald px-4 py-1.5 text-xs font-semibold text-primary-foreground">
                  Encode (FRQI)
                </button>
              </div>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "68%" }}
                  transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}
                  className="h-full bg-gradient-to-r from-emerald to-cyan-glow"
                />
              </div>
            </motion.div>
          </div>

          {/* Alignment panel */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="glass rounded-2xl p-6"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-emerald">Alignment</div>
                <div className="mt-1 font-display text-xl font-semibold">Reference vs Query</div>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <Metric label="Match" value="87.3%" color="text-emerald" />
                <Metric label="Mismatch" value="9.2%" color="text-red-400" />
                <Metric label="Gap" value="3.5%" color="text-orange-400" />
                <Metric label="Similarity" value="94.1%" color="text-cyan-400" />
              </div>
            </div>
            <div className="mt-5 space-y-2 rounded-xl bg-black/40 p-4 font-mono text-sm overflow-x-auto">
              <SequenceRow label="REF" seq={REFERENCE} compare={QUERY} mode="ref" />
              <SequenceRow label="ALN" seq={REFERENCE} compare={QUERY} mode="aln" />
              <SequenceRow label="QRY" seq={QUERY} compare={REFERENCE} mode="qry" />
            </div>
          </motion.div>

          {/* Quantum circuit */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="glass rounded-2xl p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-widest text-emerald">
                  Quantum Circuit
                </div>
                <div className="mt-1 font-display text-xl font-semibold">Grover Search Oracle</div>
              </div>
              <button className="inline-flex items-center gap-1.5 rounded-full border border-emerald/30 bg-emerald/10 px-3 py-1 text-xs text-emerald">
                <Zap className="h-3.5 w-3.5" /> Simulate
              </button>
            </div>
            <QuantumCircuit />
          </motion.div>

          {/* Charts */}
          <div className="grid gap-4 lg:grid-cols-3">
            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5 lg:col-span-2"
            >
              <ChartHeader title="Alignment Score" subtitle="Quantum vs classical over 24 runs" />
              <div className="h-56">
                <ResponsiveContainer>
                  <AreaChart data={alignmentSeries}>
                    <defs>
                      <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10B981" stopOpacity={0.6} />
                        <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="x"
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0b1a15",
                        border: "1px solid rgba(16,185,129,0.3)",
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                    <Area dataKey="classical" stroke="#38bdf8" strokeWidth={2} fill="url(#g2)" />
                    <Area dataKey="score" stroke="#10B981" strokeWidth={2} fill="url(#g1)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5"
            >
              <ChartHeader title="Quantum Speedup" subtitle="vs classical baseline" />
              <div className="h-56">
                <ResponsiveContainer>
                  <RadialBarChart
                    innerRadius="65%"
                    outerRadius="100%"
                    data={speedupData}
                    startAngle={90}
                    endAngle={-270}
                  >
                    <RadialBar
                      background={{ fill: "rgba(255,255,255,0.05)" }}
                      dataKey="value"
                      cornerRadius={20}
                    />
                  </RadialBarChart>
                </ResponsiveContainer>
                <div className="-mt-40 flex flex-col items-center justify-center text-center pointer-events-none">
                  <div className="font-display text-4xl font-semibold text-gradient-emerald">
                    7.8×
                  </div>
                  <div className="text-xs text-muted-foreground">Grover advantage</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5"
            >
              <ChartHeader title="Mutation Frequency" subtitle="Per chromosome" />
              <div className="h-56">
                <ResponsiveContainer>
                  <BarChart data={mutationData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#94a3b8", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#94a3b8", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0b1a15",
                        border: "1px solid rgba(16,185,129,0.3)",
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="freq" fill="#10B981" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5"
            >
              <ChartHeader title="Base Distribution" subtitle="Nucleotide composition" />
              <div className="h-56">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={baseDist}
                      dataKey="value"
                      innerRadius={45}
                      outerRadius={80}
                      paddingAngle={4}
                      strokeWidth={0}
                    >
                      {baseDist.map((b) => (
                        <Cell key={b.name} fill={b.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#0b1a15",
                        border: "1px solid rgba(16,185,129,0.3)",
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex justify-center gap-3 text-xs">
                {baseDist.map((b) => (
                  <div key={b.name} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ background: b.color }} />
                    {b.name} {b.value}%
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5"
            >
              <ChartHeader title="Execution Time" subtitle="Circuit depth vs runtime" />
              <div className="h-56">
                <ResponsiveContainer>
                  <LineChart data={alignmentSeries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="x"
                      tick={{ fill: "#94a3b8", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#94a3b8", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0b1a15",
                        border: "1px solid rgba(16,185,129,0.3)",
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                    <Line dataKey="score" stroke="#10B981" strokeWidth={2} dot={false} />
                    <Line
                      dataKey="classical"
                      stroke="#38bdf8"
                      strokeWidth={2}
                      dot={false}
                      strokeDasharray="4 4"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          </div>

          {/* Analytics */}
          <div className="grid gap-4 lg:grid-cols-3">
            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5 lg:col-span-2"
            >
              <ChartHeader title="Mutation Heatmap" subtitle="Position × sample intensity" />
              <Heatmap />
            </motion.div>
            <motion.div
              variants={fadeUp}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="glass rounded-2xl p-5 space-y-4"
            >
              <ChartHeader title="Genome Analytics" subtitle="Statistical summary" />
              <MetricBar label="GC Content" value={54} />
              <MetricBar label="AT Content" value={46} />
              <MetricBar label="Genome Similarity" value={94} />
              <MetricBar label="Conservation" value={81} />
              <div className="pt-2 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Phylogenetic preview</span>
                <button className="text-emerald hover:underline inline-flex items-center gap-1">
                  Open <ArrowUpRight className="h-3 w-3" />
                </button>
              </div>
              <div className="h-24 rounded-lg border border-white/5 bg-gradient-to-br from-emerald/5 to-cyan-glow/5 relative overflow-hidden">
                <svg viewBox="0 0 200 80" className="h-full w-full">
                  <g stroke="#10B981" strokeWidth="1.2" fill="none" opacity="0.7">
                    <path d="M10 40 L60 40 L60 20 L110 20" />
                    <path d="M60 40 L60 60 L110 60" />
                    <path d="M110 20 L110 10 L180 10" />
                    <path d="M110 20 L110 30 L180 30" />
                    <path d="M110 60 L110 50 L180 50" />
                    <path d="M110 60 L110 70 L180 70" />
                  </g>
                  {[10, 30, 50, 70].map((y) => (
                    <circle key={y} cx={180} cy={y} r="3" fill="#10B981" />
                  ))}
                </svg>
              </div>
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  delta,
  positive = true,
  data,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  delta: string;
  positive?: boolean;
  data: Array<{ v: number }>;
}) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ y: -3 }}
      className="glass relative overflow-hidden rounded-2xl p-5"
    >
      <div className="flex items-center justify-between">
        <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-emerald/15 text-emerald">
          <Icon className="h-4 w-4" />
        </div>
        <span className={`text-xs font-medium ${positive ? "text-emerald" : "text-cyan-400"}`}>
          {delta}
        </span>
      </div>
      <div className="mt-4 text-xs text-muted-foreground">{label}</div>
      <div className="font-display text-3xl font-semibold tracking-tight">{value}</div>
      <div className="mt-2 h-10 -mx-2">
        <ResponsiveContainer>
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`s-${label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10B981" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area dataKey="v" stroke="#10B981" strokeWidth={1.5} fill={`url(#s-${label})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: color, boxShadow: `0 0 8px ${color}` }}
      />
      {label}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="text-right">
      <div className={`font-mono font-semibold ${color}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
    </div>
  );
}

function SequenceRow({
  label,
  seq,
  compare,
  mode,
}: {
  label: string;
  seq: string;
  compare: string;
  mode: "ref" | "aln" | "qry";
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-10 shrink-0 text-[10px] uppercase text-muted-foreground">{label}</span>
      <div className="flex flex-wrap">
        {seq.split("").map((b, i) => {
          const other = compare[i];
          let cls = BASE_COLOR[b] ?? "text-muted-foreground";
          if (mode === "aln") {
            if (b === "-" || other === "-")
              return (
                <span key={i} className="text-orange-400 px-[1px]">
                  |
                </span>
              );
            return b === other ? (
              <span key={i} className="text-emerald px-[1px]">
                |
              </span>
            ) : (
              <span key={i} className="text-red-400 px-[1px]">
                ×
              </span>
            );
          }
          if (b === "-") cls = "text-orange-400";
          else if (mode !== "ref" && other && b !== other && other !== "-")
            cls = "text-red-400 bg-red-500/10 rounded";
          return (
            <span key={i} className={`px-[1px] ${cls}`}>
              {b}
            </span>
          );
        })}
      </div>
    </div>
  );
}

const GATES = [
  { name: "H", color: "#10B981" },
  { name: "X", color: "#38bdf8" },
  { name: "●", color: "#eab308" },
  { name: "R", color: "#a78bfa" },
  { name: "O", color: "#ef4444" },
  { name: "H", color: "#10B981" },
  { name: "M", color: "#94a3b8" },
];

function QuantumCircuit() {
  return (
    <div className="mt-5 space-y-6 overflow-x-auto">
      {[0, 1, 2, 3].map((q) => (
        <div key={q} className="relative flex items-center gap-2 min-w-[600px]">
          <div className="w-10 font-mono text-xs text-emerald">|q{q}⟩</div>
          <div className="relative flex-1 h-8">
            <div className="absolute left-0 right-0 top-1/2 h-px bg-gradient-to-r from-emerald/60 via-emerald/30 to-cyan-glow/60" />
            <div className="relative flex justify-between h-full items-center px-4">
              {GATES.map((g, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.5 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: (i + q) * 0.05 }}
                  className="relative flex h-8 w-8 items-center justify-center rounded-md border font-mono text-xs font-bold"
                  style={{
                    borderColor: g.color,
                    color: g.color,
                    background: `${g.color}15`,
                    boxShadow: `0 0 12px ${g.color}40`,
                  }}
                >
                  {g.name}
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      ))}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground pt-2 border-t border-white/5">
        <span className="text-emerald">H — Hadamard</span>
        <span className="text-cyan-400">X — NOT</span>
        <span className="text-yellow-400">● — Control</span>
        <span className="text-violet-400">R — Rotation</span>
        <span className="text-red-400">O — Oracle</span>
        <span>M — Measurement</span>
      </div>
    </div>
  );
}

function Heatmap() {
  const rows = 8,
    cols = 24;
  return (
    <div className="mt-4 grid gap-1" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
      {Array.from({ length: rows * cols }).map((_, i) => {
        const v = Math.random();
        const c =
          v > 0.75
            ? "rgb(239,68,68)"
            : v > 0.5
              ? "rgb(234,179,8)"
              : v > 0.25
                ? "rgb(16,185,129)"
                : "rgb(56,189,248)";
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 0.85 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.003 }}
            className="aspect-square rounded-sm"
            style={{ background: c, opacity: 0.15 + v * 0.7 }}
          />
        );
      })}
    </div>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono text-emerald">{value}%</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className="h-full bg-gradient-to-r from-emerald to-cyan-glow"
        />
      </div>
    </div>
  );
}

function ChartHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-2 flex items-start justify-between">
      <div>
        <div className="font-display text-base font-semibold">{title}</div>
        <div className="text-xs text-muted-foreground">{subtitle}</div>
      </div>
    </div>
  );
}
