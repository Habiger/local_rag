import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "@mantine/core/styles.css";
import "./globals.css";
import DashboardLayout from "@/components/DashboardLayout";

import {
  ColorSchemeScript,
  MantineProvider,
  mantineHtmlProps,
} from "@mantine/core";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAG Admin Dashboard",
  description: "Manage your RAG documents and data",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" {...mantineHtmlProps} className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <ColorSchemeScript />
        <MantineProvider>
          <DashboardLayout>
            {children}
          </DashboardLayout>
        </MantineProvider>
      </body>
    </html>
  );
}