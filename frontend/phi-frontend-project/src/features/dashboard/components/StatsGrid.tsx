import { FileStack, Layers, User, Phone, Building2, IdCard, Mail } from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import { computeTodayCount, computeTotalRedactions } from "@/lib/historyStats";
import type { HistoryEntry } from "@/lib/types/history";

export function StatsGrid({ entries }: { entries: HistoryEntry[] }) {
  const today = computeTodayCount(entries);
  const total = computeTotalRedactions(entries);
  const sum = (key: keyof HistoryEntry["counts"]) =>
    entries.reduce((s, e) => s + (e.counts[key] ?? 0), 0);

  const cards = [
    { label: "Today's requests", value: today, icon: FileStack, color: "#0891B2" },
    { label: "Total redactions", value: total, icon: Layers, color: "#059669" },
    { label: "Names found", value: sum("names_found"), icon: User, color: "#22D3EE" },
    { label: "Phones found", value: sum("phones_found"), icon: Phone, color: "#0E7490" },
    { label: "Facilities found", value: sum("facilities_found"), icon: Building2, color: "#059669" },
    { label: "MRNs found", value: sum("mrns_found"), icon: IdCard, color: "#D97706" },
    { label: "Emails found", value: sum("emails_found"), icon: Mail, color: "#0369A1" },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
      {cards.map((card, idx) => (
        <StatCard key={card.label} {...card} delay={idx * 0.04} />
      ))}
    </div>
  );
}
