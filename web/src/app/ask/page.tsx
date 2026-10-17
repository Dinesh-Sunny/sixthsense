import { AskBox } from "@/components/AskBox";
import { Atmosphere } from "@/components/Atmosphere";
import { Panel, PanelHeading } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { AppHeader } from "@/components/AppHeader";
import { COPY } from "@/lib/copy";

export default function AskPage() {
  return (
    <Atmosphere variant="soft">
      <AppHeader />
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
