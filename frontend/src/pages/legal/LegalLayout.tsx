import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Footer, LandingNavbar } from "../../components/landing";
import { Container } from "../../components/ui/Container/Container";
import { paths } from "../../lib/routes";

export interface LegalSection {
  id: string;
  title: string;
  body: ReactNode;
}

export function LegalLayout({ title, updated, intro, sections }: { title: string; updated: string; intro: ReactNode; sections: LegalSection[] }) {
  return (
    <div className="landing">
      <LandingNavbar />
      <main className="py-12 md:py-16">
        <Container>
          <article className="mx-auto max-w-[65ch] text-ink">
            <p className="text-sm text-ink-soft">Last updated {updated}</p>
            <h1 className="mt-2 text-3xl font-bold md:text-4xl">{title}</h1>
            <div className="mt-4 text-lg text-ink-soft">{intro}</div>

            <nav aria-label="On this page" className="mt-8 rounded-xl border border-line p-5">
              <p className="text-sm font-semibold">On this page</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                {sections.map((s) => (
                  <li key={s.id}>
                    <a href={`#${s.id}`} className="text-brand underline underline-offset-4">
                      {s.title}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>

            {sections.map((s, i) => (
              <section key={s.id} id={s.id} aria-labelledby={`${s.id}-h`} className="mt-10 scroll-mt-24">
                <h2 id={`${s.id}-h`} className="text-xl font-semibold">
                  {i + 1}. {s.title}
                </h2>
                <div className="mt-3 space-y-3 text-ink-soft [&_li]:mt-1 [&_ul]:list-disc [&_ul]:pl-5">{s.body}</div>
              </section>
            ))}

            <p className="mt-12 border-t border-line pt-6 text-sm text-ink-soft">
              Questions about this page? Signed-in users can raise a concern from Settings, under Support.{" "}
              <Link to={paths.home} className="text-brand underline underline-offset-4">
                Back to the home page
              </Link>
            </p>
          </article>
        </Container>
      </main>
      <Footer />
    </div>
  );
}
