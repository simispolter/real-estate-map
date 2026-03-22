import type { PropsWithChildren } from "react";
import Link from "next/link";

import { publicNavigation } from "@/lib/content";

export function PublicShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Public Workspace</p>
          <h1 className="shell-title">Residential Real-Estate Intelligence</h1>
          <p className="panel-copy">Map-first public browsing for Israeli public-company residential projects.</p>
        </div>
        <nav className="nav-links" aria-label="Primary">
          {publicNavigation.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="content-stack">{children}</main>
    </div>
  );
}
