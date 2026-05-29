import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/query-provider";
import { AppHeader } from "@/components/layout/app-header";

export const metadata: Metadata = {
  title: "Orca Trading Yuki",
  description: "Trading Intelligence Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased font-sans">
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-50">
        <QueryProvider>
          <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-6 w-full">
            <AppHeader />
            {children}
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
