import type { Metadata } from "next";
import { IBM_Plex_Mono, Public_Sans, Source_Serif_4 } from "next/font/google";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const sans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-public-sans",
});

const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-ibm-plex-mono",
});

export const metadata: Metadata = {
  title: {
    default: "aus-gov-map — Commonwealth public data",
    template: "%s · aus-gov-map",
  },
  description:
    "A living map of Australian federal government public data. Stage 2: Senate Estimates plus a sourced decision / duty map.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en-AU"
      className={`${sans.variable} ${serif.variable} ${mono.variable}`}
    >
      <body className={`${sans.className} bg-paper text-ink antialiased`}>
        <SiteHeader />
        <main className="mx-auto w-full max-w-6xl px-5 py-10">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
