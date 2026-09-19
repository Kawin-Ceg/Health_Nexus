import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { insights, type ChartRow } from "../../../content/landing";
import { Reveal } from "../../animations/Reveal/Reveal";
import { Badge } from "../../ui/Badge/Badge";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import styles from "./CommunityInsights.module.css";

const SERIES = ["normal", "elevated", "high"] as const;
type Series = (typeof SERIES)[number];

const numberFormat = new Intl.NumberFormat();

interface TooltipBodyProps {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ payload?: ChartRow }>;
}

function TooltipBody({ active, label, payload }: TooltipBodyProps) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  const total = row.normal + row.elevated + row.high;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipLabel}>{label}</p>
      <dl className={styles.tooltipRows}>
        {[...SERIES].reverse().map((key) => (
          <div key={key} className={styles.tooltipRow}>
            <dt>
              <span className={`${styles.swatch} ${styles[key]}`} aria-hidden="true" />
              {insights.legend[key]}
            </dt>
            <dd>{numberFormat.format(row[key])}</dd>
          </div>
        ))}
        <div className={`${styles.tooltipRow} ${styles.tooltipTotal}`}>
          <dt>{insights.tooltipTotal}</dt>
          <dd>{numberFormat.format(total)}</dd>
        </div>
      </dl>
    </div>
  );
}

/** Default export so the page can load it with React.lazy (keeps Recharts out of the main chunk). */
export default function CommunityInsights() {
  const { heading } = insights;
  return (
    <section id={insights.id} className={styles.section} aria-labelledby={insights.headingId}>
      <Container>
        <Reveal className={styles.header}>
          <Eyebrow>{insights.eyebrow}</Eyebrow>
          <h2 id={insights.headingId} className={styles.title}>
            {heading.lead}
            <em>{heading.emphasis}</em>
            {heading.tail}
          </h2>
          <p className={styles.body}>{insights.body}</p>
        </Reveal>

        <div className={styles.layout}>
          <Reveal delay={1} className={styles.chartCard}>
            <figure className={styles.figure}>
              <div className={styles.chartTop}>
                <figcaption className={styles.chartTitle}>{insights.chartTitle}</figcaption>
                <Badge>{insights.illustrative}</Badge>
              </div>
              <p className="visually-hidden">{insights.chartSummary}</p>

              <ul className={styles.legend}>
                {SERIES.map((key: Series) => (
                  <li key={key} className={styles.legendItem}>
                    <span className={`${styles.swatch} ${styles[key]}`} aria-hidden="true" />
                    {insights.legend[key]}
                  </li>
                ))}
              </ul>

              <div className={styles.chart} aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={insights.data} accessibilityLayer={false} margin={{ top: 8, right: 0, bottom: 0, left: -12 }} barCategoryGap="22%">
                    <CartesianGrid vertical={false} className={styles.grid} />
                    <XAxis dataKey="period" tickLine={false} axisLine={false} className={styles.axis} />
                    <YAxis tickLine={false} axisLine={false} width={48} className={styles.axis} />
                    <Tooltip content={<TooltipBody />} cursor={{ className: styles.cursor }} />
                    <Bar dataKey="normal" stackId="s" className={styles.normal} isAnimationActive={false} />
                    <Bar dataKey="elevated" stackId="s" className={styles.elevated} isAnimationActive={false} />
                    <Bar dataKey="high" stackId="s" className={styles.high} radius={[6, 6, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
          </Reveal>

          <ul className={styles.stats}>
            {insights.stats.map((stat, i) => (
              <Reveal as="li" key={stat.label} delay={(i + 2) as 2 | 3 | 4} className={styles.stat}>
                <p className={styles.statValue}>{stat.value}</p>
                <p className={styles.statLabel}>{stat.label}</p>
              </Reveal>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  );
}
