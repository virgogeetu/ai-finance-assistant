from __future__ import annotations

from ..utils.parsing import fmt_money, parse_goal
from ..utils.projections import plan_goal
from .base import BaseAgent


class GoalPlanningAgent(BaseAgent):
    name = "goal_planning"
    title = "Goal plan"
    description = "Savings goals, retirement targets, projections and 'how much should I save' questions."
    role_prompt = ("Explain the goal projection clearly: assumptions, monthly amount, range of outcomes, and "
                   "the levers the user controls (time, contributions, risk). Assumptions are illustrative.")
    rag_categories = ["retirement", "budgeting", "investing_strategy", "basics"]

    def _run(self, state):
        profile = state.get("user_profile") or {}
        ctx = state.get("context") or {}
        g = {**ctx.get("last_goal", {}), **parse_goal(state["query"])}
        if "target" not in g or "years" not in g:
            missing = [x for x in ("target amount", "time horizon") if (x == "target amount" and "target" not in g)
                       or (x == "time horizon" and "years" not in g)]
            return self.result(
                f"I can project this goal once I know your {' and '.join(missing)}. For example: "
                "_\"I want $40,000 for a home down payment in 5 years, I have $8k saved and can invest $400 a month.\"_",
                data={"needs_input": missing, "goal": g}, confidence=0.5)

        risk = profile.get("risk_profile", "moderate")
        plan = plan_goal(g["target"], g["years"], g.get("present", 0.0), g.get("monthly"), risk,
                         annual_return=g.get("rate"))
        lines = [f"**Goal:** {fmt_money(plan['target'])} in {plan['years']:g} years "
                 f"(starting from {fmt_money(plan['present'])}).",
                 f"**Assumption:** {plan['assumed_return']:.1%} average annual return "
                 f"({plan['risk_profile'] if 'rate' in g else plan['risk_profile'] + ' profile'}). "
                 "Real returns vary year to year.",
                 f"**Monthly amount needed:** about {fmt_money(plan['required_monthly'])}."]
        if g.get("monthly") is not None:
            lines.append(f"**At your {fmt_money(plan['monthly_contribution'])}/month:** projected "
                         f"{fmt_money(plan['projected_value'])} — {'on track ✅' if plan['on_track'] else 'short of the goal'}.")
            m = plan.get("months_to_goal_at_current_rate")
            if m:
                lines.append(f"At that pace you'd reach the goal in about {m // 12} years {m % 12} months.")
        mc = plan.get("monte_carlo")
        if mc:
            lines.append(f"**Range of outcomes (1,000 simulations):** pessimistic (10th pct) {fmt_money(mc['p10_final'])}, "
                         f"median {fmt_money(mc['median_final'])}, optimistic (90th pct) {fmt_money(mc['p90_final'])}; "
                         f"reached the goal in {mc['success_probability']:.0%} of simulations.")
        lines.append(f"**Inflation check:** at 2.5%/yr, {fmt_money(plan['target'])} then buys what about "
                     f"{fmt_money(plan['target_in_todays_dollars'])} buys today.")
        if plan["years"] <= 3 and "rate" not in g:
            lines.append("For goals under ~3 years, many people keep the money in stable accounts (high-yield savings, "
                         "CDs, T-bills) rather than stocks, so the projection uses a cash-like return.")
        draft = "\n\n".join(lines)  # blank lines: Markdown keeps one item per paragraph
        chunks = self.retrieve(state["query"] + " compound interest savings goal time horizon", k=3)
        content = self.compose(state, draft, chunks)
        return self.result(content, sources=self.sources_from(chunks), confidence=0.85,
                           data={"plan": plan, "goal": g})
