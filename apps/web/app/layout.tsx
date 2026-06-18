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
            <div className="space-x-4">
              <a href="/" className="hover:text-blue-100">Dashboard</a>
              <a href="/niches" className="hover:text-blue-100">Niches</a>
              <a href="/competitors" className="hover:text-blue-100">Competitors</a>
              <a href="/ideas" className="hover:text-blue-100">Ideas</a>
              <a href="/scripts" className="hover:text-blue-100">Scripts</a>
              <a href="/asset-pack" className="hover:text-blue-100">Assets</a>
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
