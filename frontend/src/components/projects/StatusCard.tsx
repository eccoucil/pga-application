"use client"

import { Shield, Clock, Activity, CheckCircle2 } from 'lucide-react'
import { StatCard } from '@/components/ui/stats'

interface StatusCardProps {
  label: string
  value: number
  color: 'cyan' | 'orange' | 'blue' | 'green'
}

const iconMap = {
  'Total Projects': Shield,
  'Planning': Clock,
  'In Progress': Activity,
  'Completed': CheckCircle2,
}

export function StatusCard({ label, value, color }: StatusCardProps) {
  const Icon = iconMap[label as keyof typeof iconMap] || Shield

  return (
    <StatCard
      label={label}
      value={value}
      icon={Icon}
      color={color}
    />
  )
}
