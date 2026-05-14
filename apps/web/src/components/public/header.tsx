import Link from "next/link";

import Image from "next/image";
import Logo from "@/public/Delight Web.png"
import { ThemeToggle } from "@/components/theme-toggle";
import { SITE_NAME } from "@/lib/site";

export function SiteHeader() {
  return (
    <header className="border-b border-border bg-bg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-serif text-xl">
          <div className="flex items-center gap-2">
            <Image src={Logo} alt="Delight Web Logo" className="w-auto h-10"/>
            <span className="font-poppins font-semibold">{SITE_NAME}</span>
          </div>
          
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-fg-muted hover:text-fg">Home</Link>
          <Link href="/search" className="text-fg-muted hover:text-fg">Search</Link>
          <Link href="/about" className="text-fg-muted hover:text-fg">About</Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
