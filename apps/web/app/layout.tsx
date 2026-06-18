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
              <a href="/admin" className="hover:text-blue-100">📊 Admin</a>
              <a href="/optimize" className="hover:text-blue-100">✨ Optimize</a>
              <a href="/voice" className="hover:text-blue-100">🎙️ Voice</a>
              <a href="/multi-platform" className="hover:text-blue-100">📱 Multi</a>
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
