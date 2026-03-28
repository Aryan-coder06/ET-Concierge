import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import { FirebaseAuthProvider } from "@/components/auth/FirebaseAuthProvider";
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
  icons: {
    icon: "/final_favicon.png",
    shortcut: "/final_favicon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="bg-[#F0F0F0] font-sans text-[#121212] antialiased">
        <FirebaseAuthProvider>{children}</FirebaseAuthProvider>
      </body>
    </html>
  );
}
