import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Handholding Content Engine",
  description: "Create a successful YouTube channel with AI help",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-blue-600 text-white shadow-lg">
          <div className="container flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold">Handholding Content Engine</h1>
            <div className="space-x-4 text-sm">
              <a href="/" className="hover:text-blue-100">Dashboard</a>
              <a href="/voice" className="hover:text-blue-100">🎙️ Voice</a>
              <a href="/auto" className="hover:text-blue-100">Auto</a>
              <a href="/full-auto" className="hover:text-blue-100">Full Auto</a>
            </div>
          </div>
        </nav>
        <main className="container py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
