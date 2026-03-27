import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import { etCompassContent } from "@/content/etCompassContent";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: etCompassContent.brand.name,
  description: etCompassContent.footer.description,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="bg-[#F0F0F0] font-sans text-[#121212] antialiased">
        {children}
      </body>
    </html>
  );
}
