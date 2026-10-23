import Link from "next/link";
import { siteSummary } from "@/lib/site-data";

const navigation = [
  { href: "/", label: "Overview", icon: "◫" },
  { href: "/organizations", label: "Organizations", icon: "▤" },
  { href: "/prospects", label: "People", icon: "◎" },
  { href: "/campaigns", label: "Campaign activity", icon: "↗" },
  { href: "/segments", label: "Segments & scoring", icon: "◌" },
  { href: "/data", label: "Data operations", icon: "⌁" },
];

export function AppShell({ children, active }: { children: React.ReactNode; active: string }) {
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="CSAF Prospect workspace home">
          <span className="brand-mark"><span /></span>
          <span className="brand-copy"><b>CSAF</b><small>Prospect workspace</small></span>
        </Link>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <Link key={item.href} href={item.href} title={item.label} aria-current={active === item.href ? "page" : undefined} className={`nav-link ${active === item.href ? "active" : ""}`}>
              <span className="nav-icon">{item.icon}</span><span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-card">
            <span className="connection-orb" />
            <div><b>IRS filing analysis</b><small>Updated {siteSummary.generatedAt}</small></div>
          </div>
          <div className="profile-row"><div className="avatar">CS</div><div><b>CSAF workspace</b><small>Executive workspace</small></div></div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>CSAF</span><i>/</i><b>{navigation.find((item) => item.href === active)?.label}</b></div>
          <div className="topbar-right"><span className="snapshot-pill"><span /> Data updated {siteSummary.generatedAt}</span></div>
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="header-action">{action}</div>}</div>;
}

export function Notice({ children, tone = "info" }: { children: React.ReactNode; tone?: "info" | "warning" }) {
  return <div className={`notice notice-${tone}`}><span className="notice-symbol">{tone === "warning" ? "!" : "i"}</span><div>{children}</div></div>;
}
