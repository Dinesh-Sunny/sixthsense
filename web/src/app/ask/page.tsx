import Link from "next/link";
import { AskBox } from "@/components/AskBox";
import { Atmosphere } from "@/components/Atmosphere";
import { Panel, PanelHeading } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { Wordmark } from "@/components/Wordmark";
import { Button } from "@/components/ui/button";
import { COPY } from "@/lib/copy";

export default function AskPage() {
  return (
    <Atmosphere variant="soft">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-5 md:px-8">
        <Button asChild variant="glass" size="sm">
          <Link href="/">← {COPY.allMoments}</Link>
        </Button>
        <Wordmark />
      </header>
      <main className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 pb-8">
        <Panel aria-labelledby="ask-page-h">
          <PanelHeading id="ask-page-h">{COPY.askLabel}</PanelHeading>
          <AskBox />
        </Panel>
      </main>
      <SiteFooter />
    </Atmosphere>
  );
}
