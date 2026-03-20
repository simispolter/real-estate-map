import type { PropsWithChildren } from "react";
import Link from "next/link";

import { adminNavigation } from "@/lib/content";

export function AdminShell({ children }: PropsWithChildren) {
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div>
          <p className="eyebrow">Admin Workspace</p>
          <h1 className="shell-title">Internal review console</h1>
          <p className="panel-copy">
            Public exploration and internal correction are separated from the first sprint.
          </p>
        </div>
        <nav className="admin-nav" aria-label="Admin">
          {adminNavigation.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="content-stack">{children}</main>
    </div>
  );
}
