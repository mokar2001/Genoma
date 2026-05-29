import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Dna,
  Brain,
  Microscope,
  Atom,
  ArrowRight,
  Clock,
  ChevronRight,
  Zap,
} from "lucide-react";

const TOOLS = [
  {
    icon: Brain,
    color: "from-indigo-500 to-blue-600",
    name: "DeepRare",
    tagline: "Phenotype + Genotype Ranking",
    desc: "Analyzes patient symptoms and genetic variants simultaneously to rank the most likely rare diseases with transparent reasoning.",
  },
  {
    icon: Microscope,
    color: "from-violet-500 to-purple-600",
    name: "ACMG Classifier",
    tagline: "Variant Pathogenicity",
    desc: "Applies ACMG/AMP 2015 criteria to classify every variant — separating actionable pathogenic mutations from harmless noise.",
  },
  {
    icon: Atom,
    color: "from-fuchsia-500 to-pink-600",
    name: "AlphaFold3",
    tagline: "3D Structural Analysis",
    desc: "Visualizes wild-type vs. mutant protein structures to show exactly why a variant disrupts protein function at the molecular level.",
  },
];

const STATS = [
  { value: "5–7 yrs", label: "Avg. rare disease diagnosis time", icon: Clock },
  { value: "~4 min", label: "With RareDx AI pipeline", icon: Zap },
  { value: "300M+", label: "People affected by rare diseases", icon: Dna },
];

const DEMO_CASES = [
  {
    id: "marfan",
    name: "Marfan Syndrome",
    gene: "FBN1 c.3463C>T",
    desc: "Connective tissue disorder with aortic root dilation",
    color: "border-l-indigo-500",
  },
  {
    id: "brca1",
    name: "Hereditary Breast Cancer",
    gene: "BRCA1 c.5266dupC",
    desc: "Frameshift variant — BRCT domain truncation",
    color: "border-l-violet-500",
  },
  {
    id: "wilson",
    name: "Wilson's Disease",
    gene: "ATP7B compound het.",
    desc: "Autosomal recessive copper metabolism disorder",
    color: "border-l-fuchsia-500",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12 space-y-24">
      {/* Hero */}
      <motion.section
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center space-y-6"
      >
        <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-4 py-1.5 text-sm font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
          <Zap className="h-3.5 w-3.5" />
          AI-Powered Rare Disease Diagnostics
        </div>
        <h1 className="text-5xl font-bold tracking-tight text-slate-900 dark:text-white lg:text-6xl">
          From Symptom to{" "}
          <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
            Molecular Cause
          </span>
          <br />
          in Minutes
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-slate-600 dark:text-slate-400">
          RareDx combines three state-of-the-art AI tools to compress the 5–7 year
          rare disease diagnostic odyssey into a transparent, evidence-backed pipeline.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/diagnose"
            className="gradient-brand flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:opacity-90"
          >
            Start Diagnosis <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#demo"
            className="flex items-center gap-2 rounded-xl border px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Try Demo Cases
          </a>
        </div>
      </motion.section>

      {/* Stats */}
      <section className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {STATS.map(({ value, label, icon: Icon }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            className="card p-6 text-center"
          >
            <Icon className="mx-auto mb-3 h-8 w-8 text-indigo-500" />
            <p className="text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
            <p className="mt-1 text-sm text-slate-500">{label}</p>
          </motion.div>
        ))}
      </section>

      {/* Tools */}
      <section>
        <h2 className="mb-8 text-center text-2xl font-bold text-slate-900 dark:text-white">
          The Three-Tool Pipeline
        </h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {TOOLS.map(({ icon: Icon, color, name, tagline, desc }, i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 * i }}
              className="card p-6 space-y-4"
            >
              <div
                className={`inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${color} shadow-md`}
              >
                <Icon className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="font-bold text-slate-900 dark:text-white">{name}</p>
                <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400">{tagline}</p>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{desc}</p>
              <div className="flex items-center text-xs font-medium text-indigo-600 dark:text-indigo-400">
                {i === 0 ? "Step 1" : i === 1 ? "Step 2" : "Step 3"}
                <ChevronRight className="h-3 w-3 ml-1" />
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Demo Cases */}
      <section id="demo">
        <h2 className="mb-6 text-center text-2xl font-bold text-slate-900 dark:text-white">
          Pre-loaded Demo Cases
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {DEMO_CASES.map(({ id, name, gene, desc, color }) => (
            <Link
              key={id}
              to={`/diagnose?demo=${id}`}
              className={`card border-l-4 ${color} p-5 hover:shadow-md transition-shadow space-y-1`}
            >
              <p className="font-semibold text-slate-900 dark:text-white">{name}</p>
              <p className="font-mono text-xs text-indigo-600 dark:text-indigo-400">{gene}</p>
              <p className="text-xs text-slate-500">{desc}</p>
              <div className="flex items-center gap-1 pt-2 text-xs font-medium text-indigo-600 dark:text-indigo-400">
                Load case <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
