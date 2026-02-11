"use client"

import { Users, UserCheck, UserX, TrendingUp, LucideIcon } from "lucide-react";

export interface StatCardProps {
  label: string;
  value: number | string;
  icon?: LucideIcon;
  color?: "purple" | "emerald" | "rose" | "cyan" | "orange" | "blue" | "green";
  subtitle?: string;
  subtitleColor?: "green" | "slate" | "rose";
  loading?: boolean;
}

const colorMap = {
  purple: {
    hoverBorder: "hover:border-purple-500/30",
    gradient: "from-purple-500/5",
    iconBg: "bg-purple-500/10",
    iconBorder: "border-purple-500/10",
    iconColor: "text-purple-400",
  },
  emerald: {
    hoverBorder: "hover:border-emerald-500/30",
    gradient: "from-emerald-500/5",
    iconBg: "bg-emerald-500/10",
    iconBorder: "border-emerald-500/10",
    iconColor: "text-emerald-400",
  },
  rose: {
    hoverBorder: "hover:border-rose-500/30",
    gradient: "from-rose-500/5",
    iconBg: "bg-rose-500/10",
    iconBorder: "border-rose-500/10",
    iconColor: "text-rose-400",
  },
  cyan: {
    hoverBorder: "hover:border-cyan-500/30",
    gradient: "from-cyan-500/5",
    iconBg: "bg-cyan-500/10",
    iconBorder: "border-cyan-500/10",
    iconColor: "text-cyan-400",
  },
  orange: {
    hoverBorder: "hover:border-orange-500/30",
    gradient: "from-orange-500/5",
    iconBg: "bg-orange-500/10",
    iconBorder: "border-orange-500/10",
    iconColor: "text-orange-400",
  },
  blue: {
    hoverBorder: "hover:border-blue-500/30",
    gradient: "from-blue-500/5",
    iconBg: "bg-blue-500/10",
    iconBorder: "border-blue-500/10",
    iconColor: "text-blue-400",
  },
  green: {
    hoverBorder: "hover:border-green-500/30",
    gradient: "from-green-500/5",
    iconBg: "bg-green-500/10",
    iconBorder: "border-green-500/10",
    iconColor: "text-green-400",
  },
};

const subtitleColorMap = {
  green: "text-green-400",
  slate: "text-slate-500",
  rose: "text-rose-400",
};

export function StatCard({
  label,
  value,
  icon: Icon,
  color = "purple",
  subtitle,
  subtitleColor = "slate",
  loading = false,
}: StatCardProps) {
  const colors = colorMap[color];
  const DisplayIcon = Icon || Users;

  return (
    <div
      className={`group relative p-6 bg-[#0f1016]/60 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden ${colors.hoverBorder} transition-all duration-300`}
    >
      <div
        className={`absolute inset-0 bg-gradient-to-br ${colors.gradient} via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity`}
      ></div>
      <div className="relative flex items-center justify-between">
        <div>
          <p className="text-slate-400 text-sm font-medium mb-1">{label}</p>
          <h3 className="text-3xl font-bold text-white tracking-tight">
            {loading ? (
              <span className="inline-block animate-pulse">...</span>
            ) : (
              value
            )}
          </h3>
          {subtitle && (
            <div className="flex items-center gap-1 mt-2 text-xs">
              {subtitleColor === "green" && <TrendingUp className="w-3 h-3" />}
              <span className={subtitleColorMap[subtitleColor]}>{subtitle}</span>
            </div>
          )}
        </div>
        <div
          className={`w-12 h-12 rounded-xl ${colors.iconBg} flex items-center justify-center ${colors.iconColor} border ${colors.iconBorder} group-hover:scale-110 transition-transform duration-300`}
        >
          <DisplayIcon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

export interface StatsProps {
  stats: { total: number; active: number; inactive: number };
  loading?: boolean;
}

export function Stats({ stats, loading = false }: StatsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {/* Total Clients */}
      <StatCard
        label="Total Clients"
        value={stats.total}
        icon={Users}
        color="purple"
        subtitle="+12% from last month"
        subtitleColor="green"
        loading={loading}
      />

      {/* Active Clients */}
      <StatCard
        label="Active Clients"
        value={stats.active}
        icon={UserCheck}
        color="emerald"
        subtitle="Currently monitoring"
        subtitleColor="slate"
        loading={loading}
      />

      {/* Inactive Clients */}
      <StatCard
        label="Inactive Clients"
        value={stats.inactive}
        icon={UserX}
        color="rose"
        subtitle="Requires attention"
        subtitleColor="rose"
        loading={loading}
      />
    </div>
  );
}
