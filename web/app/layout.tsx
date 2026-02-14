import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "next-themes";
import { SuppressConsoleWarnings } from "@/components/suppress-console-warnings";
import { AuthGuard } from "@/components/auth-guard";
import { LayoutWrapper } from "@/components/layout-wrapper";

export const metadata: Metadata = {
  title: "Business Center Management Dashboard",
  description: "Admin dashboard for business center service ticket management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className="antialiased">
        <SuppressConsoleWarnings />
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthGuard>
            <LayoutWrapper>{children}</LayoutWrapper>
          </AuthGuard>
        </ThemeProvider>
      </body>
    </html>
  );
}
