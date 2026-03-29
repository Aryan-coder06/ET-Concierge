export const PRODUCT_PROMPTS: Record<string, string> = {
  "ET Prime":
    "Explain how ET Prime fits into my current ET journey, what it unlocks, and whether it should be my first step.",
  "ET Markets":
    "Show me the best ET Markets tools for my current goal and explain when to use each one.",
  "ET Portfolio":
    "Show me how ET Portfolio can help me track holdings, goals, SIPs, and alerts inside my ET journey.",
  "ET Wealth Edition":
    "Explain how ET Wealth Edition fits into a money and investing journey and when I should use it.",
  "ET Print Edition":
    "Tell me when ET Print Edition is the right ET surface for me and how it complements other ET products.",
  ETMasterclass:
    "Show me the best ET Masterclass and learning path for my current goals and experience level.",
  "ET Events":
    "Show me the most relevant ET events, summits, and communities for my profile and what I should explore first.",
  "ET Partner Benefits":
    "Explain which ET Partner Benefits matter for me, how they work, and what I should verify before activating them.",
  "ET Edge Events":
    "Show me the ET Edge event and summit path most relevant to my profile and why it matters.",
};

export const USE_CASE_PROMPTS: Record<string, string> = {
  "EXPLORE ET PRIME SMARTER":
    "Explain how ET Prime should fit into my ET journey, what I should read first, and whether it is my best starting point.",
  "FIND THE RIGHT MARKETS TOOLS":
    "Show me the right ET Markets tools for my goal, explain what each tool does, and tell me which one I should start with first.",
  "DISCOVER LEARNING AND EVENTS":
    "Show me the best ET learning, masterclass, and event path for my interests and explain how these ET experiences connect together.",
  "ASK WHAT FITS YOU BEST":
    "Ask one or two smart questions, then tell me what ET path fits me best and why.",
};

export function buildSearchPromptHref(prompt: string) {
  return `/search?prompt=${encodeURIComponent(prompt)}`;
}

export function getPromptForProduct(product?: string | null) {
  if (!product) return undefined;
  return PRODUCT_PROMPTS[product];
}

export function getPromptForUseCase(title?: string | null) {
  if (!title) return undefined;
  return USE_CASE_PROMPTS[title];
}
