import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

const links = [
  { to: "/collections/upload", label: "Upload" },
  { to: "/collections/runs", label: "Runs" },
] as const

export function CollectionsNav() {
  return (
    <nav className="mb-6 flex items-center gap-1 border-b pb-3">
      <Link
        to="/"
        className="mr-4 text-sm font-semibold text-muted-foreground hover:text-foreground"
      >
        Collections
      </Link>
      {links.map((link) => (
        <Link
          key={link.to}
          to={link.to}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
          activeProps={{ className: "bg-accent text-accent-foreground" }}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  )
}
