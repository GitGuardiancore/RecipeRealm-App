# Architecture

Alien Terminal is a pipeline: signals come in, get interpreted through an alien cognitive framework, and go out as social media posts. The interesting decisions are in how the persona stays consistent, how memory creates continuity, and how the pipeline avoids the failure modes of autonomous agents.

## The persona constraint

The alien persona is not a character sheet that the LLM reads once and forgets. It is a system prompt that enforces specific structural rules on every output: third-person reference to humans, clinical emotional register, concrete signal references, confident misinterpretation through the cognitive framework, and zero AI self-awareness.

The system prompt was tuned over many iterations to avoid two failure modes. First, collapsing into a generic "wise alien" voice that sounds like a fortune cookie — vague platitudes about humanity. The fix was requiring every observation to name the specific signal being interpreted. Second, breaking character into helpful-assistant mode with disclaimers and hedging. The fix was explicitly forbidding meta-commentary and making the alien unaware it is an LLM.

The cognitive categories (territorial-display, resource-hoarding, etc.) are the alien's taxonomy. They are not labels for the human reader; they are how the alien organizes its understanding of the species. When the memory context includes earlier observations tagged with categories, the LLM naturally builds connections: "another instance of territorial-display, consistent with the pattern from the previous signal batch."

## Why memory matters

Without memory, the alien generates isolated observations. Each signal interpretation starts from scratch. The alien never says "this contradicts earlier readings" or "the resource-hoarding frequency is increasing" because it has no earlier readings to reference.

The memory window is the last N observations (default 10) injected into the interpreter's message list as "previous field notes." This is cheap and effective. The LLM sees the recent observation history and naturally produces callbacks, contradictions, and running theories. The memory is not a RAG system or a vector store — it is a literal text dump of recent field notes. This works because the observations are short (1-3 sentences each) and the window is small enough to fit comfortably in the context budget.

The memory window trades off recency vs context budget. Ten observations at 1-3 sentences each is roughly 200-600 tokens — well within budget even for smaller models. Increasing the window to 50 would give the alien more history but would start to compete with the system prompt for attention. Ten is the sweet spot for the current persona complexity.

## Why RSS feeds

The signal sources need to be diverse, public, and structured. RSS meets all three. News feeds give the alien geopolitical signals. Tech feeds give it technology signals. Science feeds give it research signals. The alien needs variety to develop interesting cross-category theories.

We considered scraping trending topics from X directly. We chose not to because trending topics are noisy, often lack context (a trending hashtag alone is not a signal the alien can interpret meaningfully), and scraping X is against their ToS. RSS feeds are stable, structured, and legal.

We also considered using a news API (Google News, NewsAPI). RSS is free, requires no API key, and is harder to break. The feeds sometimes go down or change format, but the interceptor handles failures gracefully — a failed feed is logged and skipped, not fatal.

## Why the composer exists

The LLM generates field notes. The composer validates them. This separation exists because LLMs occasionally break character. The composer catches emoji that sneak through, hashtags the model adds despite being told not to, exclamation marks that violate the alien's emotional register, and AI self-references that break immersion.

The composer also handles the 280-character trim. The interpreter has no length constraint — it produces the observation the alien wants to make. The composer shapes that observation into a deliverable post, trimming at sentence boundaries to avoid mid-word cuts.

## Why dry-run mode is the default

The agent posts to a real X account. A misconfigured deployment could spam the account with broken or off-brand posts. Dry-run mode logs what would be posted without calling the X API. The operator verifies the output, then flips the flag. This is a safety rail, not a testing convenience.

## What we considered and didn't ship

- **Mention responses.** The alien could respond to people who reply to its posts. We decided against it because the persona is an observer, not a conversationalist. Responding to humans would break the frame.
- **Image generation.** The alien could generate diagrams or sketches of what it observes. We cut this for v1 to keep the pipeline simple. The text output is the product; images are a future addition.
- **Multiple personas.** We considered two aliens with different cognitive frameworks arguing about the same signals (inspired by Inkwell's two-agent model). We cut this because the single-alien voice is already distinctive enough and a second persona would dilute focus.
- **Vector memory.** We considered using embeddings to retrieve thematically similar past observations instead of just the most recent N. The overhead was not justified for the current observation rate (a few posts per day). If the agent scales to dozens of observations per day, semantic retrieval would make the callbacks more interesting.
- **Autonomous scheduling.** The alien could decide when to post based on signal urgency or novelty. We chose operator-controlled scheduling because autonomous timing adds complexity without clear benefit. The alien's value is in what it says, not when it says it.
