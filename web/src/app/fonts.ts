// Only font importer. Google Fonts is blocked in the build workspace, so fonts ship locally.
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import localFont from "next/font/local";

export const instrumentSerif = localFont({
  src: [
    { path: "./fonts/instrument-serif-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/instrument-serif-latin-400-italic.woff2", weight: "400", style: "italic" },
  ],
  variable: "--font-instrument",
  display: "swap",
});

export const fontVariables = `${GeistSans.variable} ${GeistMono.variable} ${instrumentSerif.variable}`;
