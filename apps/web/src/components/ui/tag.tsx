type TagTone = "default" | "accent" | "warning";

const toneClassName: Record<TagTone, string> = {
  default: "tag",
  accent: "tag tag-accent",
  warning: "tag tag-warning",
};

export function Tag({ children, tone = "default" }: { children: string; tone?: TagTone }) {
  return <span className={toneClassName[tone]}>{children}</span>;
}
