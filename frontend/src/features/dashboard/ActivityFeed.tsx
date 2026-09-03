interface ActivityFeedProps {
  events: { text: string; at: string }[];
}

function relativeTime(at: string): string {
  const days = Math.floor((Date.now() - new Date(at).getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "today";
  if (days === 1) return "1 d ago";
  return `${days} d ago`;
}

export function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Recent activity</h2>
      {events.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nothing yet — tick a skill or submit a project to get started.</p>
      ) : (
        <ul className="divide-y">
          {events.map((e, i) => (
            <li key={i} className="flex items-baseline justify-between gap-4 py-2 text-sm">
              <span>{e.text}</span>
              <span className="shrink-0 text-xs text-muted-foreground">{relativeTime(e.at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
