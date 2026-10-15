import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { insights, type ChartRow } from "../../../content/landing";
import { Badge } from "../../ui/Badge/Badge";
import { Container } from "../../ui/Container/Container";
import { Eyebrow } from "../Eyebrow/Eyebrow";
import { BlurIn } from "../BlurIn/BlurIn";
import { Doodle } from "../Doodle/Doodle";
import styles from "./CommunityInsights.module.css";

const SERIES = ["normal", "elevated", "high"] as const;
type Series = (typeof SERIES)[number];

const numberFormat = new Intl.NumberFormat("en-IN");
const total = (row: ChartRow) => row.normal + row.elevated + row.high;
const thisWeek = insights.data[insights.data.length - 1];

interface TooltipBodyProps {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ payload?: ChartRow }>;
}

function TooltipBody({ active, label, payload }: TooltipBodyProps) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
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
          <dd>{numberFormat.format(total(row))}</dd>
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
      <Doodle piece="ecg" className={styles.ecg} />
      <Doodle piece="honeycomb" className={styles.honeycomb} delay={2} />
      <Doodle piece="botanical" className={styles.botanical} delay={3} />
      <Container>
        <BlurIn className={styles.header}>
          <Eyebrow>{insights.eyebrow}</Eyebrow>
          <h2 id={insights.headingId} className={styles.title}>
            {heading}
          </h2>
          <p className={styles.body}>{insights.body}</p>
        </BlurIn>

        <div className={styles.layout}>
          <BlurIn delay={1} className={styles.chartCard}>
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
                  <BarChart data={insights.data} accessibilityLayer={false} margin={{ top: 8, right: 0, bottom: 0, left: 0 }} barCategoryGap="22%">
                    <CartesianGrid vertical={false} className={styles.grid} />
                    <XAxis dataKey="period" tickLine={false} axisLine={false} className={styles.axis} />
                    <YAxis tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => numberFormat.format(v)} className={styles.axis} />
                    <Tooltip content={<TooltipBody />} cursor={{ className: styles.cursor }} />
                    <Bar dataKey="normal" stackId="s" className={styles.normal} isAnimationActive={false} />
                    <Bar dataKey="elevated" stackId="s" className={styles.elevated} isAnimationActive={false} />
                    <Bar dataKey="high" stackId="s" className={styles.high} radius={[6, 6, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className={styles.periodNote}>{insights.periodNote}</p>
              <details className={styles.dataTable}>
                <summary>{insights.tableToggle}</summary>
                <table>
                  <thead>
                    <tr>
                      <th scope="col">{insights.tableColumns.period}</th>
                      {SERIES.map((key) => (
                        <th key={key} scope="col">{insights.legend[key]}</th>
                      ))}
                      <th scope="col">{insights.tableColumns.total}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.data.map((row) => (
                      <tr key={row.period}>
                        <th scope="row">{row.period}</th>
                        {SERIES.map((key) => (
                          <td key={key}>{numberFormat.format(row[key])}</td>
                        ))}
                        <td>{numberFormat.format(total(row))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </figure>
          </BlurIn>

          <ul className={styles.stats}>
            {[
              { value: numberFormat.format(total(thisWeek)), label: insights.stats.thisWeek },
              { value: numberFormat.format(thisWeek.elevated + thisWeek.high), label: insights.stats.aboveUsual },
              insights.stats.areas,
            ].map((stat) => (
              <li key={stat.label} className={styles.stat}>
                <p className={styles.statValue}>{stat.value}</p>
                <p className={styles.statLabel}>{stat.label}</p>
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  );
}
