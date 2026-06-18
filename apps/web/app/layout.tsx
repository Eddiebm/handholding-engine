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
            <a href="/" className="text-2xl font-bold hover:text-blue-100">Handholding</a>
            <div className="space-x-4 text-sm">
              <a href="/" className="hover:text-blue-100">Dashboard</a>
              <a href="/voice" className="hover:text-blue-100">🎙️ Voice</a>
              <a href="/auto" className="hover:text-blue-100">YouTube</a>
              <a href="/multi-platform" className="hover:text-blue-100">📱 Multi-Platform</a>
              <a href="/landing" className="hover:text-blue-100">About</a>
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
