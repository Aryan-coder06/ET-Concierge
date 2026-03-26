"use client";

import Link from "next/link";
import { useState } from "react";
import FloatingChatButton from "@/components/FloatingChatButton";
type ShapeKind =
  | "circle"
  | "square"
  | "triangle"
  | "diamond"
  | "ring"
  | "pill"
  | "bars";

type StatItem = {
  id: string;
  value: string;
  label: string;
  shape: ShapeKind;
  shapeClass: string;
};

type BlogPost = {
  date: string;
  author: string;
  title: string;
  description: string;
  artClass: string;
};

type FeatureCard = {
  title: string;
  description: string;
  shape: ShapeKind;
  shapeClass: string;
};

type Step = {
  title: string;
  description: string;
  shapeClass: string;
};

type Benefit = {
  title: string;
  description: string;
};

type Testimonial = {
  quote: string;
  name: string;
  role: string;
  accent: string;
};

type PricingTier = {
  name: string;
  price: string;
  suffix: string;
  description: string;
  features: string[];
  featured?: boolean;
  badge?: string;
  cta: string;
};

type FooterGroup = {
  title: string;
  links: string[];
};

const navLinks = [
  { label: "Product", href: "#product" },
  { label: "Insights", href: "#blog" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
];

const stats: StatItem[] = [
  {
    id: "1",
    value: "500K+",
    label: "Active Users",
    shape: "circle",
    shapeClass: "bg-[#D02020] rounded-full",
  },
  {
    id: "2",
    value: "99.99%",
    label: "Uptime SLA",
    shape: "square",
    shapeClass: "bg-[#1040C0]",
  },
  {
    id: "3",
    value: "24/7",
    label: "Support Access",
    shape: "diamond",
    shapeClass: "bg-[#F0C020] text-white",
  },
  {
    id: "4",
    value: "$10M+",
    label: "Customer Savings",
    shape: "ring",
    shapeClass: "bg-[#D02020] rounded-full",
  },
];

const sponsors = [
  {
    title: "StarterApp",
    description:
      "StarterApp is your done-for-you SaaS foundation—AI-first, context-engineered, and built with a modern product UX.",
    accent: "bg-[#D02020]",
    link: "#",
  },
  {
    title: "Your Brand Here",
    description:
      "Place your sponsor block here later. The card structure and spacing already match the original Bauhaus design.",
    accent: "bg-[#1040C0]",
    link: "#",
  },
];

const blogPosts: BlogPost[] = [
  {
    date: "2025-01-15",
    author: "Sarah Chen",
    title: "Boosting Team Productivity with AI Automation",
    description:
      "Discover how intelligent automation can revolutionize your workflow and free up valuable time for innovation.",
    artClass: "bg-[#D02020]",
  },
  {
    date: "2025-01-10",
    author: "Marcus Rodriguez",
    title: "The Future of Collaboration: Real-time & Seamless",
    description:
      "Explore how real-time tools are shaping the way modern teams connect, share, and execute faster.",
    artClass: "bg-[#F0C020]",
  },
  {
    date: "2025-01-05",
    author: "Elena Popov",
    title: "Scaling Your SaaS with Global Infrastructure",
    description:
      "Learn how to support global users with speed, stability, and infrastructure built for growth.",
    artClass: "bg-white",
  },
];

const features: FeatureCard[] = [
  {
    title: "Real-time Collaboration",
    description:
      "Work together seamlessly with your team. Share updates, communicate instantly, and stay aligned on every project.",
    shape: "circle",
    shapeClass: "bg-[#D02020]",
  },
  {
    title: "Smart Automation",
    description:
      "Automate repetitive tasks and workflows. Save hours every week and focus on what matters most.",
    shape: "triangle",
    shapeClass: "bg-[#F0C020]",
  },
  {
    title: "Advanced Analytics",
    description:
      "Get actionable insights with powerful reporting tools and make data-driven decisions with confidence.",
    shape: "square",
    shapeClass: "bg-[#1040C0]",
  },
  {
    title: "Seamless Integrations",
    description:
      "Connect with your favorite tools and fit neatly into your existing workflow and tech stack.",
    shape: "diamond",
    shapeClass: "bg-[#D02020]",
  },
  {
    title: "Enterprise Security",
    description:
      "Bank-level encryption and security protocols so your data stays protected at every layer.",
    shape: "ring",
    shapeClass: "bg-[#1040C0]",
  },
  {
    title: "24/7 Support",
    description:
      "Get help whenever you need it. Expert support is always ready to assist your team.",
    shape: "pill",
    shapeClass: "bg-[#F0C020]",
  },
  {
    title: "Global Infrastructure",
    description:
      "Deploy instantly to 35+ regions worldwide and ensure low latency for all your users.",
    shape: "bars",
    shapeClass: "bg-[#121212]",
  },
];

const steps: Step[] = [
  {
    title: "Connect your data",
    description:
      "Integrate with your existing tools in one click. We support major platforms out of the box.",
    shapeClass: "bg-[#D02020]",
  },
  {
    title: "Configure workflows",
    description:
      "Use a visual builder to set up processes. No coding required—just drag, drop, and refine.",
    shapeClass: "bg-[#1040C0]",
  },
  {
    title: "Start collaborating",
    description:
      "Invite your team and start working immediately. Track progress and measure results in real time.",
    shapeClass: "bg-[#F0C020]",
  },
];

const benefits: Benefit[] = [
  {
    title: "Save time and resources",
    description:
      "Reduce manual work by up to 60% with intelligent automation and streamlined processes.",
  },
  {
    title: "Improve team productivity",
    description:
      "Give your team the tools they need to collaborate effectively and deliver faster.",
  },
  {
    title: "Scale with confidence",
    description:
      "Built to grow with your business—from startup teams to enterprise operations.",
  },
  {
    title: "Stay organized",
    description:
      "Keep all your work in one place. No more scattered tools, lost files, or missed deadlines.",
  },
];

const testimonials: Testimonial[] = [
  {
    quote:
      '"Acme has completely transformed how our team operates. We saw a 40% increase in productivity from day one."',
    name: "Sarah Chen",
    role: "Product Director at TechFlow",
    accent: "bg-[#D02020]",
  },
  {
    quote:
      '"The automation features alone are worth the price. It feels like having an extra team member working 24/7."',
    name: "Marcus Rodriguez",
    role: "CTO at InnovateLab",
    accent: "bg-[#1040C0]",
  },
  {
    quote:
      '"Simple, intuitive, and powerful. Easily the best project management tool we have used in years."',
    name: "Elena Popov",
    role: "VP of Operations at CloudScale",
    accent: "bg-[#F0C020]",
  },
  {
    quote:
      '"Stability is unmatched. We migrated our infrastructure in less than a week with zero downtime."',
    name: "David Kim",
    role: "DevOps Lead at CloudNet",
    accent: "bg-[#D02020]",
  },
  {
    quote:
      '"Scaled with us from day one. From 10 users to 10,000, the platform never skipped a beat."',
    name: "Jessica Wu",
    role: "Founder at StartUp X",
    accent: "bg-[#1040C0]",
  },
  {
    quote:
      '"The analytics are a game changer. We finally have clear visibility into team performance."',
    name: "Alex Thompson",
    role: "Product Manager at Enterprise Corp",
    accent: "bg-[#F0C020]",
  },
];

const pricing: PricingTier[] = [
  {
    name: "Starter",
    price: "USD29",
    suffix: "/month",
    description: "Perfect for small teams just getting started",
    features: [
      "Up to 10 team members",
      "5 GB storage",
      "Basic integrations",
      "Email support",
      "Mobile apps",
      "Basic analytics",
    ],
    cta: "Start free trial",
  },
  {
    name: "Professional",
    price: "USD79",
    suffix: "/month",
    description: "For growing teams that need more power",
    features: [
      "Up to 50 team members",
      "100 GB storage",
      "Advanced integrations",
      "Priority support",
      "Mobile apps",
      "Advanced analytics",
      "Custom workflows",
      "API access",
    ],
    featured: true,
    badge: "Best Value",
    cta: "Start free trial",
  },
  {
    name: "Enterprise",
    price: "Custom",
    suffix: "",
    description: "For organizations that need advanced features and support",
    features: [
      "Unlimited team members",
      "Unlimited storage",
      "All integrations",
      "24/7 dedicated support",
      "Advanced analytics",
      "Custom workflows",
      "API access",
      "SSO & SAML",
      "Advanced security",
      "Dedicated account manager",
      "Custom SLA",
    ],
    cta: "Contact sales",
  },
];

const faqs = [
  {
    question: "How does the free trial work?",
    answer:
      "Start your 14-day free trial with no credit card required. You'll have full access to all features in your chosen plan. Cancel anytime during the trial period without being charged.",
  },
  {
    question: "Can I change plans later?",
    answer:
      "Yes. You can upgrade or downgrade your plan at any time. Changes take effect immediately, and charges are prorated accordingly.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards, along with PayPal and wire transfers for annual plans.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Absolutely. We use bank-level SSL encryption for data transmission and storage and follow strong compliance practices.",
  },
  {
    question: "Do you offer discounts for annual plans?",
    answer:
      "Yes. Annual billing comes with a discount and helps simplify procurement for larger teams.",
  },
  {
    question: "What kind of support do you provide?",
    answer:
      "All plans include email support. Professional plans get priority support, while enterprise plans receive dedicated assistance.",
  },
];

const footerGroups: FooterGroup[] = [
  {
    title: "Product",
    links: ["Features", "Pricing", "Security", "Integrations", "Changelog"],
  },
  {
    title: "Company",
    links: ["About", "Blog", "Careers", "Contact"],
  },
  {
    title: "Resources",
    links: ["Documentation", "Help Center", "API Reference", "Community"],
  },
  {
    title: "Legal",
    links: ["Privacy Policy", "Terms of Service", "Cookie Policy", "GDPR"],
  },
];

const btnBase =
  "inline-flex items-center justify-center border-2 border-black font-bold uppercase tracking-wider transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none";
const btnPrimary =
  `${btnBase} bg-[#D02020] text-white shadow-[4px_4px_0px_0px_#121212] hover:bg-[#ba1b1b]`;
const btnSecondary =
  `${btnBase} bg-white text-[#121212] shadow-[4px_4px_0px_0px_#121212] hover:bg-[#F0F0F0]`;

function LogoMark() {
  return (
    <div className="flex items-center gap-1.5 sm:gap-2">
      <div className="h-6 w-6 rounded-full border-2 border-black bg-[#D02020] sm:h-8 sm:w-8" />
      <div className="h-6 w-6 border-2 border-black bg-[#1040C0] sm:h-8 sm:w-8" />
      <div
        className="h-6 w-6 border-2 border-black bg-[#F0C020] sm:h-8 sm:w-8"
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    </div>
  );
}

function ArrowRightIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

function PlayIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 5.5v13l10-6.5-10-6.5Z" />
    </svg>
  );
}

function ChevronDownIcon({
  className = "h-5 w-5",
}: {
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function ShapeGlyph({
  kind,
  className,
}: {
  kind: ShapeKind;
  className: string;
}) {
  if (kind === "circle") {
    return <div className={`h-12 w-12 rounded-full border-2 border-black ${className}`} />;
  }

  if (kind === "square") {
    return <div className={`h-12 w-12 border-2 border-black ${className}`} />;
  }

  if (kind === "triangle") {
    return (
      <div
        className={`h-12 w-12 border-2 border-black ${className}`}
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    );
  }

  if (kind === "diamond") {
    return (
      <div
        className={`h-12 w-12 rotate-45 border-2 border-black ${className}`}
      />
    );
  }

  if (kind === "ring") {
    return (
      <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-black bg-white">
        <div className={`h-6 w-6 rounded-full border-2 border-black ${className}`} />
      </div>
    );
  }

  if (kind === "pill") {
    return <div className={`h-12 w-16 rounded-full border-2 border-black ${className}`} />;
  }

  return (
    <div className="flex h-12 w-12 items-center justify-center gap-1 border-2 border-black bg-white px-1">
      <span className={`h-7 w-1.5 ${className}`} />
      <span className={`h-9 w-1.5 ${className}`} />
      <span className={`h-5 w-1.5 ${className}`} />
    </div>
  );
}

function AvatarStamp({
  name,
  accent,
}: {
  name: string;
  accent: string;
}) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("");

  return (
    <div
      className={`flex h-12 w-12 items-center justify-center rounded-full border-2 border-black font-black uppercase ${accent}`}
    >
      {initials}
    </div>
  );
}

function PosterArt({ accent }: { accent: string }) {
  return (
    <div className={`relative aspect-[4/3] overflow-hidden border-4 border-black ${accent}`}>
      <div className="absolute inset-0 dot-grid-dark opacity-50" />
      <div className="absolute right-6 top-6 h-16 w-16 rounded-full border-4 border-black bg-white" />
      <div className="absolute bottom-6 left-6 h-20 w-20 border-4 border-black bg-[#F0C020]" />
      <div
        className="absolute bottom-8 right-10 h-16 w-16 border-4 border-black bg-[#D02020]"
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    </div>
  );
}

export default function HomePage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(0);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F0F0F0] text-[#121212] selection:bg-[#F0C020] selection:text-black">
      <FloatingChatButton />

      <nav className="sticky top-0 z-50 border-b-4 border-black bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:h-20 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-1.5 sm:gap-2">
            <LogoMark />
            <span className="ml-1 font-black text-lg uppercase tracking-tighter sm:ml-2 sm:text-2xl">
              ET /
            </span>
          </Link>

          <div className="hidden items-center gap-4 md:flex">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="inline-flex h-12 items-center px-6 font-bold uppercase tracking-wider transition-colors hover:bg-[#E0E0E0]"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/search"
              className={`${btnSecondary} h-12 rounded-full px-6 text-sm`}
            >
              Log In
            </Link>
            <Link
              href="/search"
              className={`${btnPrimary} h-12 rounded-none px-6 text-sm`}
            >
              AI Concierge
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen((prev) => !prev)}
            className="flex h-10 w-10 flex-col items-center justify-center gap-1.5 border-2 border-black bg-white shadow-[2px_2px_0px_0px_black] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none md:hidden"
            aria-label="Open menu"
          >
            <span className="h-0.5 w-6 bg-black" />
            <span className="h-0.5 w-6 bg-black" />
            <span className="h-0.5 w-6 bg-black" />
          </button>
        </div>

        {mobileOpen && (
          <div className="border-t-4 border-black bg-white md:hidden">
            <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6">
              {navLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="border-2 border-black px-4 py-3 font-bold uppercase tracking-wide"
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href="/search"
                onClick={() => setMobileOpen(false)}
                className={`${btnPrimary} justify-center px-4 py-3`}
              >
                Open AI Concierge
              </Link>
            </div>
          </div>
        )}
      </nav>

      <main>
        <section className="relative overflow-hidden border-b-4 border-black">
          <div className="grid min-h-[80vh] grid-cols-1 lg:grid-cols-2">
            <div className="relative z-10 flex flex-col justify-center bg-white p-6 sm:p-12 lg:border-r-4 lg:border-black lg:p-24">
              <div className="absolute left-0 top-0 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#F0C020] opacity-50 sm:h-32 sm:w-32" />

              <h1 className="mb-6 font-black uppercase leading-[0.9] tracking-tighter text-4xl sm:mb-8 sm:text-6xl lg:text-8xl">
                Transform the way your team works
              </h1>

              <p className="mb-8 max-w-md border-l-4 border-[#D02020] pl-4 text-lg font-medium leading-relaxed sm:mb-12 sm:border-l-8 sm:pl-6 sm:text-xl lg:text-2xl">
                A Bauhaus-style landing page converted fully into Next.js,
                TypeScript, and Tailwind—ready for your ET AI Concierge content.
              </p>

              <div className="flex flex-col gap-4 sm:flex-row">
                <Link
                  href="/search"
                  className={`${btnPrimary} h-14 w-full rounded-none px-8 text-base sm:w-auto sm:text-lg lg:text-xl`}
                >
                  Open AI Concierge
                </Link>

                <button
                  type="button"
                  className={`${btnSecondary} h-14 w-full gap-2 rounded-none px-8 text-base sm:w-auto sm:text-lg lg:text-xl`}
                >
                  <PlayIcon className="h-5 w-5" />
                  Watch demo
                </button>
              </div>

              <div className="mt-8 flex flex-col items-start gap-3 text-xs font-bold uppercase tracking-widest sm:mt-12 sm:flex-row sm:items-center sm:gap-4 sm:text-sm">
                <div className="-space-x-2 flex">
                  <AvatarStamp name="Sarah Chen" accent="bg-[#D02020]" />
                  <AvatarStamp name="Drew Cano" accent="bg-[#1040C0]" />
                  <AvatarStamp name="Koray Okumus" accent="bg-[#F0C020]" />
                  <AvatarStamp name="Lana Steiner" accent="bg-white" />
                </div>
                <span>Join 50,000+ teams already using ET /</span>
              </div>
            </div>

            <div className="relative flex min-h-[400px] items-center justify-center overflow-hidden bg-[#1040C0] p-8 sm:p-12">
              <div className="dot-grid absolute inset-0 opacity-20" />

              <div className="relative aspect-square w-full max-w-md">
                <div className="absolute right-0 top-0 h-2/3 w-2/3 rounded-full border-4 border-black bg-[#F0C020] shadow-[8px_8px_0px_0px_black]" />
                <div className="absolute bottom-0 left-0 h-2/3 w-2/3 rotate-45 border-4 border-black bg-[#D02020] shadow-[8px_8px_0px_0px_black]" />
                <div className="absolute left-1/2 top-1/2 z-10 flex h-1/2 w-1/2 -translate-x-1/2 -translate-y-1/2 items-center justify-center border-4 border-black bg-white shadow-[8px_8px_0px_0px_black]">
                  <div
                    className="h-16 w-16 bg-black"
                    style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section
          id="product"
          className="border-b-4 border-black bg-[#F0F0F0] py-16 sm:py-24 lg:py-32"
        >
          <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
            <div>
              <h2 className="mb-6 font-black uppercase leading-[0.95] tracking-tight text-4xl sm:text-6xl lg:text-7xl">
                Experience the future of team collaboration with our unified,
                intelligent platform today.
              </h2>
            </div>

            <div className="space-y-6 text-lg font-medium leading-relaxed sm:text-xl">
              <p>
                This section mirrors the original long-form supporting copy
                block. Replace this later with your Economic Times AI Concierge
                positioning, assistant benefits, or newsroom workflow story.
              </p>
              <p>
                The layout, spacing, borders, typography, and contrast are
                already set up so you can just swap copy without touching the
                visual system.
              </p>
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#F0C020]">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 divide-y-4 divide-black md:grid-cols-2 md:divide-x-4 md:divide-y-0 lg:grid-cols-4">
              {stats.map((item) => (
                <div
                  key={item.id}
                  className="group flex flex-col items-center bg-white p-8 text-center transition-colors hover:bg-[#F0F0F0] sm:p-10 lg:p-12"
                >
                  <div className="mb-4 flex h-16 w-16 items-center justify-center">
                    <ShapeGlyph
                      kind={item.shape}
                      className={`${item.shapeClass} shadow-[4px_4px_0px_0px_black]`}
                    />
                  </div>
                  <div className="mb-2 font-black tracking-tighter text-3xl sm:text-4xl lg:text-5xl">
                    {item.value}
                  </div>
                  <div className="text-xs font-bold uppercase tracking-wider sm:text-sm">
                    {item.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#F0F0F0] py-16 sm:py-24 lg:py-32">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-12 text-center sm:mb-16 lg:mb-24">
              <h2 className="mb-4 font-black uppercase text-4xl sm:mb-6 sm:text-6xl lg:text-8xl">
                Our Sponsors
              </h2>
              <p className="text-lg font-bold uppercase tracking-widest sm:text-xl lg:text-2xl">
                Design-ready blocks you can later replace with real partners
              </p>
            </div>

            <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
              {sponsors.map((item) => (
                <a key={item.title} href={item.link} className="group block">
                  <div className="flex h-full flex-col border-4 border-black bg-white p-6 shadow-[10px_10px_0px_0px_black] transition-transform duration-200 hover:-translate-y-2 sm:p-8">
                    <div className="mb-8">
                      <div className="flex aspect-square w-full items-center justify-center overflow-hidden border-4 border-black p-6 shadow-[8px_8px_0px_0px_black]">
                        <PosterArt accent={item.accent} />
                      </div>
                    </div>

                    <h3 className="mb-4 text-center font-black uppercase text-3xl sm:text-4xl">
                      {item.title}
                    </h3>

                    <p className="mb-8 text-center text-lg font-medium leading-relaxed opacity-80">
                      {item.description}
                    </p>

                    <div className="mt-auto flex justify-center">
                      <span className="inline-flex items-center border-b-4 border-[#D02020] text-lg font-black uppercase transition-colors group-hover:border-black">
                        Learn More
                        <ArrowRightIcon className="ml-2 h-6 w-6" />
                      </span>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </section>

        <section
          id="blog"
          className="border-b-4 border-black bg-[#1040C0] py-12 sm:py-16 lg:py-24"
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 className="mb-10 inline-block border-b-2 border-white pb-2 font-black uppercase text-3xl text-white sm:text-5xl lg:text-7xl">
              Latest Insights
            </h2>

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              {blogPosts.map((post) => (
                <article
                  key={post.title}
                  className="group flex h-full flex-col border-4 border-black bg-white shadow-[10px_10px_0px_0px_black] transition-transform hover:-translate-y-2"
                >
                  <div className="p-4">
                    <PosterArt accent={post.artClass} />
                  </div>

                  <div className="flex flex-1 flex-col p-6">
                    <div className="mb-4 flex flex-wrap items-center gap-3 text-sm font-bold uppercase tracking-wider">
                      <span>{post.date}</span>
                      <span className="h-2 w-2 rounded-full bg-black" />
                      <span>{post.author}</span>
                    </div>

                    <h3 className="mb-4 font-black uppercase leading-tight text-2xl">
                      {post.title}
                    </h3>

                    <p className="mb-6 flex-1 text-base font-medium leading-relaxed opacity-80">
                      {post.description}
                    </p>

                    <a
                      href="#"
                      className="inline-flex items-center text-base font-black uppercase"
                    >
                      Read Article
                      <ArrowRightIcon className="ml-2 h-5 w-5" />
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section
          id="features"
          className="relative border-b-4 border-black bg-[#F0F0F0] py-12 sm:py-16 lg:py-24"
        >
          <div className="absolute left-0 top-12 h-20 w-20 rounded-full bg-[#D02020] opacity-20" />
          <div className="absolute bottom-10 right-0 h-24 w-24 bg-[#1040C0] opacity-20" />

          <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 max-w-3xl">
              <h2 className="mb-4 font-black uppercase leading-none text-3xl sm:text-5xl lg:text-7xl">
                Built for bold product storytelling
              </h2>
              <p className="text-lg font-medium leading-relaxed sm:text-xl">
                This card grid closely follows the original visual rhythm and is
                perfect for product capabilities, ET assistant features, or use
                cases.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="group border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_black] transition-transform hover:-translate-y-2 sm:p-8"
                >
                  <div className="mb-6">
                    <ShapeGlyph
                      kind={feature.shape}
                      className={`${feature.shapeClass} shadow-[4px_4px_0px_0px_black]`}
                    />
                  </div>
                  <h3 className="mb-3 font-black uppercase text-2xl leading-tight">
                    {feature.title}
                  </h3>
                  <p className="text-base font-medium leading-relaxed opacity-80">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden border-b-4 border-black bg-white py-12 sm:py-16 lg:py-24">
          <div className="absolute inset-x-0 top-0 h-6 bg-[#F0C020]" />
          <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
            <div className="mb-12 text-center sm:mb-16">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                How it works
              </h2>
              <p className="text-lg font-bold uppercase tracking-widest opacity-70">
                Get up and running in minutes, not days
              </p>
            </div>

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              {steps.map((step, index) => (
                <div
                  key={step.title}
                  className="relative border-4 border-black bg-[#F0F0F0] p-8 shadow-[10px_10px_0px_0px_black]"
                >
                  <div className="mb-6 flex items-center gap-4">
                    <div
                      className={`flex h-14 w-14 items-center justify-center border-4 border-black text-xl font-black ${step.shapeClass}`}
                    >
                      {index + 1}
                    </div>
                    <h3 className="font-black uppercase text-2xl">{step.title}</h3>
                  </div>
                  <p className="text-lg font-medium leading-relaxed">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#D02020] py-12 text-white sm:py-16 lg:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 max-w-3xl">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                Why teams choose this layout
              </h2>
              <p className="text-lg font-bold uppercase tracking-widest text-white/80">
                Everything you need in one strong visual system
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
              {benefits.map((item) => (
                <div
                  key={item.title}
                  className="border-4 border-black bg-white p-6 text-[#121212] shadow-[8px_8px_0px_0px_black] sm:p-8"
                >
                  <h3 className="mb-3 font-black uppercase text-2xl leading-tight">
                    {item.title}
                  </h3>
                  <p className="text-base font-medium leading-relaxed opacity-80">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="overflow-hidden border-b-4 border-black bg-[#F0F0F0] py-12 sm:py-16 lg:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 text-center sm:mb-14">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                Trusted by innovative teams
              </h2>
              <p className="text-lg font-medium leading-relaxed opacity-70">
                See what customers have to say about the experience
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {testimonials.map((item) => (
                <div
                  key={item.name}
                  className="border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_black] sm:p-8"
                >
                  <div className="mb-6 flex items-center gap-4">
                    <AvatarStamp name={item.name} accent={item.accent} />
                    <div>
                      <p className="font-black uppercase text-lg">{item.name}</p>
                      <p className="text-sm font-bold uppercase tracking-wide opacity-60">
                        {item.role}
                      </p>
                    </div>
                  </div>

                  <p className="text-lg font-medium leading-relaxed">{item.quote}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          id="pricing"
          className="relative overflow-hidden border-b-4 border-black bg-white py-12 sm:py-16 lg:py-24"
        >
          <div className="absolute left-0 top-1/4 h-32 w-32 rounded-full bg-[#F0C020] opacity-10" />
          <div className="absolute bottom-1/4 right-0 h-40 w-40 bg-[#1040C0] opacity-10" />

          <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-8 text-center sm:mb-12 lg:mb-16">
              <h2 className="mb-3 font-black uppercase text-3xl sm:mb-4 sm:text-5xl lg:text-7xl">
                Simple, transparent pricing
              </h2>
              <p className="text-base font-bold uppercase text-gray-600 sm:text-lg lg:text-xl">
                Choose the plan that’s right for your team
              </p>
            </div>

            <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-3">
              {pricing.map((tier) => (
                <div
                  key={tier.name}
                  className={`relative border-4 border-black p-8 shadow-[12px_12px_0px_0px_black] ${
                    tier.featured ? "z-10 bg-[#F0C020] lg:-mt-8 lg:mb-8" : "bg-white"
                  }`}
                >
                  {tier.featured && tier.badge && (
                    <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 border-4 border-black bg-[#D02020] px-6 py-2 font-bold uppercase tracking-widest text-white shadow-[4px_4px_0px_0px_black]">
                      {tier.badge}
                    </div>
                  )}

                  <h3 className="mb-4 font-black uppercase text-3xl">{tier.name}</h3>

                  <div className="mb-6">
                    <span className="font-black text-5xl">{tier.price}</span>
                    {tier.suffix ? (
                      <span className="text-lg font-bold uppercase opacity-60">
                        {tier.suffix}
                      </span>
                    ) : null}
                  </div>

                  <p className="mb-8 border-b-4 border-black pb-8 font-medium">
                    {tier.description}
                  </p>

                  <ul className="mb-8 space-y-4">
                    {tier.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-3 font-bold"
                      >
                        <div className="mt-1 h-4 w-4 flex-shrink-0 bg-black" />
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <Link
                    href="/search"
                    className={`${
                      tier.featured ? btnPrimary : btnSecondary
                    } h-12 w-full justify-center rounded-none px-6 text-lg font-black`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          id="faq"
          className="border-b-4 border-black bg-[#F0F0F0] py-12 sm:py-16 lg:py-24"
        >
          <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
            <h2 className="mb-8 text-center font-black uppercase text-3xl sm:mb-12 sm:text-5xl lg:text-7xl">
              Frequently asked questions
            </h2>

            <div>
              {faqs.map((item, index) => {
                const open = openFaq === index;

                return (
                  <div
                    key={item.question}
                    className="mb-4 border-4 border-black bg-white shadow-[4px_4px_0px_0px_#121212]"
                  >
                    <button
                      type="button"
                      onClick={() => setOpenFaq(open ? -1 : index)}
                      className={`flex w-full items-center justify-between p-6 text-left text-xl font-bold uppercase tracking-wide transition-colors ${
                        open
                          ? "bg-[#D02020] text-white"
                          : "bg-white text-black hover:bg-[#F0F0F0]"
                      }`}
                      aria-expanded={open}
                    >
                      <span>{item.question}</span>
                      <ChevronDownIcon
                        className={`h-6 w-6 transition-transform ${
                          open ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    <div
                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                        open ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                      }`}
                    >
                      <div className="border-t-4 border-black bg-[#FFF9C4] p-6 text-lg">
                        {item.answer}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden border-b-4 border-black bg-[#F0C020] py-16 sm:py-24 lg:py-32">
          <div className="absolute -left-8 top-10 h-24 w-24 rounded-full border-4 border-black bg-white opacity-80" />
          <div className="absolute bottom-10 right-10 h-20 w-20 rotate-45 border-4 border-black bg-[#D02020]" />

          <div className="relative z-10 mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8">
            <h2 className="mb-6 font-black uppercase leading-[0.92] text-4xl sm:text-6xl lg:text-8xl">
              Ready to transform your workflow?
            </h2>
            <p className="mx-auto mb-10 max-w-3xl text-lg font-medium leading-relaxed sm:text-xl lg:text-2xl">
              Join thousands of teams already using this layout system to work
              smarter and ship faster.
            </p>

            <div className="flex flex-col justify-center gap-4 sm:flex-row">
              <Link
                href="/search"
                className={`${btnPrimary} h-14 justify-center rounded-none px-8 text-base sm:text-lg`}
              >
                Start free trial
              </Link>
              <button
                type="button"
                className={`${btnSecondary} h-14 justify-center rounded-none px-8 text-base sm:text-lg`}
              >
                Schedule a demo
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-[#121212] py-12 text-white sm:py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-16 grid grid-cols-1 gap-12 md:grid-cols-2 xl:grid-cols-5">
            <div className="md:col-span-2">
              <div className="mb-6 flex items-center gap-2">
                <LogoMark />
                <span className="ml-2 font-black uppercase tracking-tighter text-2xl">
                  ET /
                </span>
              </div>

              <p className="mb-8 max-w-md text-lg opacity-70">
                Empowering teams to work smarter.
              </p>

              <div className="flex gap-4">
                {["t", "l", "g"].map((item) => (
                  <a
                    key={item}
                    href="#"
                    className="flex h-12 w-12 items-center justify-center border-2 border-white transition-colors hover:bg-white hover:text-black"
                  >
                    <span className="font-bold text-xs uppercase">{item}</span>
                  </a>
                ))}
              </div>
            </div>

            {footerGroups.map((group) => (
              <div key={group.title}>
                <h4 className="mb-6 text-xl font-black uppercase text-[#F0C020]">
                  {group.title}
                </h4>
                <ul className="space-y-4">
                  {group.links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="group flex items-center gap-2 font-bold transition-colors hover:text-[#F0C020]"
                      >
                        <span className="h-2 w-2 bg-[#D02020] opacity-0 transition-opacity group-hover:opacity-100" />
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-4 border-t-4 border-white/20 pt-8 text-sm font-bold uppercase tracking-wide text-white/70 sm:flex-row sm:items-center sm:justify-between">
            <p>© 2025 ET / All rights reserved.</p>
            <div className="flex flex-wrap gap-4">
              <a href="#">Privacy Policy</a>
              <a href="#">Terms of Service</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}