import {
  User,
  Mail,
  Phone,
  Printer,
  Globe2,
  IdCard,
  ShieldAlert,
  Cake,
  Hash,
  MapPin,
  MapPinned,
  Building2,
  Link2,
  CreditCard,
  HeartPulse,
  Cpu,
  Car,
  BadgeCheck,
  type LucideIcon,
} from "lucide-react";
import type { EntityCountKey } from "@/lib/types/api";

export interface EntityMeta {
  key: EntityCountKey;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  /** Tailwind-safe color token used for chart fills and badges. */
  color: string;
}

export const ENTITY_META: Record<EntityCountKey, EntityMeta> = {
  names_found: {
    key: "names_found",
    label: "Names",
    shortLabel: "Names",
    icon: User,
    color: "#0891B2",
  },
  emails_found: {
    key: "emails_found",
    label: "Emails",
    shortLabel: "Emails",
    icon: Mail,
    color: "#059669",
  },
  phones_found: {
    key: "phones_found",
    label: "Phone numbers",
    shortLabel: "Phones",
    icon: Phone,
    color: "#22D3EE",
  },
  faxes_found: {
    key: "faxes_found",
    label: "Fax numbers",
    shortLabel: "Faxes",
    icon: Printer,
    color: "#0E7490",
  },
  ips_found: {
    key: "ips_found",
    label: "IP addresses",
    shortLabel: "IPs",
    icon: Globe2,
    color: "#6366F1",
  },
  mrns_found: {
    key: "mrns_found",
    label: "Medical record numbers",
    shortLabel: "MRNs",
    icon: IdCard,
    color: "#D97706",
  },
  ssns_found: {
    key: "ssns_found",
    label: "Social security numbers",
    shortLabel: "SSNs",
    icon: ShieldAlert,
    color: "#DC2626",
  },
  dobs_found: {
    key: "dobs_found",
    label: "Dates of birth",
    shortLabel: "DOBs",
    icon: Cake,
    color: "#DB2777",
  },
  ages_found: {
    key: "ages_found",
    label: "Ages over 89",
    shortLabel: "Ages",
    icon: Hash,
    color: "#9333EA",
  },
  addresses_found: {
    key: "addresses_found",
    label: "Street addresses",
    shortLabel: "Addresses",
    icon: MapPin,
    color: "#EA580C",
  },
  locations_found: {
    key: "locations_found",
    label: "Locations",
    shortLabel: "Locations",
    icon: MapPinned,
    color: "#0D9488",
  },
  facilities_found: {
    key: "facilities_found",
    label: "Facilities",
    shortLabel: "Facilities",
    icon: Building2,
    color: "#059669",
  },
  urls_found: {
    key: "urls_found",
    label: "URLs",
    shortLabel: "URLs",
    icon: Link2,
    color: "#2563EB",
  },
  account_numbers_found: {
    key: "account_numbers_found",
    label: "Account numbers",
    shortLabel: "Accounts",
    icon: CreditCard,
    color: "#7C3AED",
  },
  health_plan_ids_found: {
    key: "health_plan_ids_found",
    label: "Health plan IDs",
    shortLabel: "Plan IDs",
    icon: HeartPulse,
    color: "#DB2777",
  },
  device_ids_found: {
    key: "device_ids_found",
    label: "Device identifiers",
    shortLabel: "Devices",
    icon: Cpu,
    color: "#4F46E5",
  },
  vins_found: {
    key: "vins_found",
    label: "Vehicle ID numbers",
    shortLabel: "VINs",
    icon: Car,
    color: "#0369A1",
  },
  licenses_found: {
    key: "licenses_found",
    label: "License numbers",
    shortLabel: "Licenses",
    icon: BadgeCheck,
    color: "#B45309",
  },
};

/** The subset surfaced as headline stat cards on the dashboard. */
export const DASHBOARD_HEADLINE_KEYS: EntityCountKey[] = [
  "names_found",
  "phones_found",
  "facilities_found",
  "mrns_found",
  "emails_found",
];
