# AI SaaS Cost Advisor

**Open Agent Hackathon 2026 · Track 02: The Agent That Can Explain Why**

🎬 [Demo video link] · 📊 [Deck link]

[Screenshot]

**The problem.** A founder spent over $15,000 building with an AI app-builder, and no tool estimated what the app would cost to build or to run.

**Who it's for.** Solo founders building an AI SaaS product who need to know what their AI features will cost before they commit.

**What you get in 30 seconds.** Describe your idea and its 2–5 AI features. You get:
- the monthly AI cost for each feature at four growth stages (50, 500, 5,000 and 50,000 users);
- your revenue and AI margin at each stage, plus the first stage that goes over your budget;
- real token counts measured on your own example inputs, shown next to the estimates;
- pass/fail quality checks, flagged risks, and a full trace of every step.

**How it works.**
1. Recalls what earlier runs learned about this idea.
2. Reads dated model prices from a data layer.
3. Picks a frontier, a mid-tier and an open-source candidate model for each feature.
4. With your approval and under a spend cap you set, runs your example inputs on the models it can measure.
5. Checks the answers against your rules. A critic model flags problems.
6. Projects costs as you grow, then writes the evidence back.

Anything it couldn't measure is labelled "estimated", "projected only" or "unknown". It is never filled in.

**Sponsor tech.**
- **Zetaris** stores the price data and receives every run's evidence.
- **Meterless Nightshift** routes every model call.
- **Meterless H-MEM** is the idea's memory.
- **NVIDIA Nemotron** (Lightning and Ultra) runs the Planner and the Critic.

**Try it offline (sample mode, no accounts or network).**
```bash
git clone https://github.com/pradeepgnd/cost-optimizer && cd cost-optimizer
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
SAMPLE_MODE=true python run.py --input input_examples/example_1.json --output result.json
```
Sample mode needs no `.env`. For H-MEM memory in sample mode, also install the engine once with `(cd app/engines/hmem/reference && npm ci)` (Node 20+). Without it the run still completes, and the trace records the memory step as an error.

Open the UI with `python -m streamlit run streamlit_app.py`. Live mode setup is below.

**Limitations and disclaimer.**
- The cost figures are planning estimates, not financial, legal or investment advice. Check them against your provider's current prices and your own usage before you commit money.
- Prices come from a dated catalog snapshot and may have changed since.
- Only models with a verified rate profile are measured; the others are projected from reference prices and labelled "projected only".
- Token counts are measured on a few example inputs. Real traffic, prompt length and user behaviour will differ.
- Quality checks are deterministic rules plus human review. They do not prove a model is good enough for your product.
- Sample mode outputs are labelled `SAMPLE/OFFLINE` and use no real model calls.
