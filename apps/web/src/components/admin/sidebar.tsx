"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

const items = [
  { href: "/admin", label: "Dashboard", icon: "▦" },
  { href: "/admin/posts", label: "Posts", icon: "✎" },
  { href: "/admin/comments", label: "Comments", icon: "❝" },
  { href: "/admin/subscribers", label: "Subscribers", icon: "✉" },
  { href: "/admin/tags", label: "Tags", icon: "#" },
  { href: "/admin/series", label: "Series", icon: "≡" },
] as const;

const COLLAPSE_KEY = "admin-sidebar-collapsed";

function isActive(pathname: string, href: string): boolean {
  if (href === "/admin") {
    return pathname === "/admin";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname() ?? "/admin";
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1");
    } catch {
      // ignore
    }
  }, []);

  function toggle() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  return (
    <nav
      aria-label="Admin"
      className={cn(
        "shrink-0 border-r border-border bg-bg-elevated transition-[width] duration-200",
        collapsed ? "w-14" : "w-56",
      )}
    >
      <div className="flex items-center justify-between px-3 py-3">
        {!collapsed && <span className="font-serif text-lg">Delight</span>}
        <button
          type="button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={toggle}
          className="ml-auto rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
        >
          {collapsed ? "›" : "‹"}
        </button>
      </div>
      <ul className="space-y-1 px-2 pb-4">
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                  active
                    ? "bg-accent text-accent-fg"
                    : "text-fg-muted hover:bg-bg-muted hover:text-fg",
                  collapsed && "justify-center px-0",
                )}
              >
                <span className="w-4 text-center text-base leading-none">
                  {item.icon}
                </span>
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
