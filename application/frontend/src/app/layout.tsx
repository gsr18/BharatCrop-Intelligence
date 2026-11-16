import type { Metadata } from "next";
import "./globals.css";
import { productName } from "./product";
import { AppProviders } from "../components/app-providers";
import { AppShell } from "../components/app-shell";

export const metadata: Metadata = {
  title: productName,
  description:
    "Agricultural information and evidence-led decision support for India.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('bharatcrop-theme')||'system';document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t;var l=localStorage.getItem('bharatcrop-language');if(l==='hi'||l==='en')document.documentElement.lang=l}catch(e){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}",
          }}
        />
      </head>
      <body>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
