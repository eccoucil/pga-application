"use client"

export function Footer() {
  return (
    <footer className="px-6 py-6 border-t border-white/5 bg-black/20 backdrop-blur-sm">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-slate-400">
        <p>© 2026 PGA Portal. All rights reserved.</p>
        <div className="flex gap-6">
          <a
            href="#"
            className="hover:text-purple-400 transition-colors"
          >
            Privacy Policy
          </a>
          <a
            href="#"
            className="hover:text-purple-400 transition-colors"
          >
            Terms of Service
          </a>
          <a
            href="#"
            className="hover:text-purple-400 transition-colors"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  )
}
