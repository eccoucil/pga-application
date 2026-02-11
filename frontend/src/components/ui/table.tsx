"use client"

import { Search, Filter } from "lucide-react"
import { ReactNode } from "react"

interface TableProps {
  children: ReactNode
  searchPlaceholder?: string
  showSearch?: boolean
  showFilters?: boolean
  onSearchChange?: (value: string) => void
  onFilterClick?: () => void
}

export function Table({
  children,
  searchPlaceholder = "Search...",
  showSearch = true,
  showFilters = true,
  onSearchChange,
  onFilterClick,
}: TableProps) {
  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-xl">
      {/* Toolbar */}
      {(showSearch || showFilters) && (
        <div className="p-5 border-b border-white/5 flex gap-4">
          {showSearch && (
            <div className="flex-1 relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg blur opacity-0 group-focus-within:opacity-20 transition duration-1000 group-hover:duration-200"></div>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-purple-400 transition-colors" />
              <input
                type="text"
                placeholder={searchPlaceholder}
                onChange={(e) => onSearchChange?.(e.target.value)}
                className="relative w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all"
              />
            </div>
          )}
          {showFilters && (
            <button
              onClick={onFilterClick}
              className="flex items-center gap-2 px-4 py-2.5 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:border-purple-500/30 hover:bg-purple-500/10 transition-all"
            >
              <Filter className="w-4 h-4" />
              <span>Filters</span>
            </button>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          {children}
        </table>
      </div>
    </div>
  )
}

interface TableHeaderProps {
  children: ReactNode
}

export function TableHeader({ children }: TableHeaderProps) {
  return (
    <thead>
      <tr className="border-b border-white/5 bg-white/[0.02]">
        {children}
      </tr>
    </thead>
  )
}

interface TableHeaderCellProps {
  children: ReactNode
  className?: string
}

export function TableHeaderCell({ children, className = "" }: TableHeaderCellProps) {
  return (
    <th className={`px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider ${className}`}>
      {children}
    </th>
  )
}

interface TableBodyProps {
  children: ReactNode
}

export function TableBody({ children }: TableBodyProps) {
  return (
    <tbody className="divide-y divide-white/5">
      {children}
    </tbody>
  )
}

interface TableRowProps {
  children: ReactNode
  className?: string
}

export function TableRow({ children, className = "" }: TableRowProps) {
  return (
    <tr className={`group hover:bg-white/[0.02] transition-colors ${className}`}>
      {children}
    </tr>
  )
}

interface TableCellProps {
  children: ReactNode
  className?: string
}

export function TableCell({ children, className = "" }: TableCellProps) {
  return (
    <td className={`px-6 py-4 ${className}`}>
      {children}
    </td>
  )
}
