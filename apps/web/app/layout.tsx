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
        {children}
      </body>
    </html>
  );
}
