"use client";

import { useEffect, useState } from "react";

interface LiveProject {
  id: string;
  date: string;
  opportunity: string;
  url: string;
  score: number;
  buyer: string;
  current_status: string;
}

export default function LiveProjects() {
  const [projects, setProjects] = useState<LiveProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/lp-index.json")
      .then((res) => {
        if (!res.ok) throw new Error("Not found");
        return res.json();
      })
      .then((data: LiveProject[]) => {
        setProjects(data);
      })
      .catch(() => {
        // No LP data yet, that's fine
        setProjects([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;

  if (projects.length === 0) return null;

  return (
    <section className="live-projects anim-fade-up" aria-labelledby="lp-title">
      <div className="section-header">
        <h2 id="lp-title">Live Projects</h2>
        <p>
          Product opportunities currently being validated with landing pages.
          Each page was built in &lt;2 hours based on a single signal.
        </p>
      </div>

      <div className="lp-grid">
        {projects
          .slice()
          .reverse()
          .map((p) => (
            <a
              key={p.id}
              href={p.url}
              className="lp-card"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="lp-score">Score {p.score}</span>
              <h3>{p.opportunity}</h3>
              <div className="lp-meta">
                <span>{p.date}</span>
                <span className="lp-arrow">→</span>
              </div>
            </a>
          ))}
      </div>
    </section>
  );
}
