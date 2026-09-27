"""Least-risk route selection (R9). Routes are listed lowest-risk first."""
from __future__ import annotations

from typing import Callable

from ..models import Route


def select_routes(stage: str, available_steps: list[str], claimant_in_chain: bool, claimant_name: str,
                  licensor_name: str, status_for: Callable[[list[str]], str], dispute_components: list[str],
                  cn_core_components: list[str], cn_all_components: list[str], chosen_step: str) -> list[Route]:
    routes: list[Route] = []
    claimant = claimant_name or "the claimant"
    licensor = licensor_name or "the licensor"
    if stage in ("claim", "dispute", "appeal"):
        routes.append(Route(
            id="route_licensor_release", rank=1,
            title=f"Ask {licensor} to have its administrator release the claim",
            description=(f"Send your licence certificate and receipt to {licensor} and ask it to have {claimant} release the claim. "
                         "No platform process is started and nothing can escalate to a strike."
                         if claimant_in_chain else
                         f"Ask {licensor} whether {claimant} administers this track for it. Until that link is confirmed, this may be an ownership question rather than a licensed-use conflict."),
            step=None, evidence_status=status_for(dispute_components) if claimant_in_chain else "needs_adviser",
            sentence_id="route:1"))
        platform_step = available_steps[0] if available_steps else None
        title = {"dispute": "In-platform dispute", "appeal": "In-platform appeal", None: "In-platform dispute or appeal"}.get(platform_step, "In-platform step")
        desc = {
            "dispute": "Dispute the claim from the platform. The claimant has 30 days to respond and may instead submit a removal request, which removes the video and places a strike.",
            "appeal": "Appeal the rejected dispute. The claimant has 7 days; if it rejects the appeal it must submit a removal request, which removes the video and places a strike.",
        }.get(platform_step, "No in-platform step is currently available at this stage.")
        routes.append(Route(id="route_platform", rank=2, title=title, description=desc, step=platform_step,
                            evidence_status=status_for(dispute_components) if platform_step else "needs_adviser",
                            sentence_id="route:2", is_chosen_step=(platform_step == chosen_step)))
    elif stage == "removed_with_strike":
        routes.append(Route(
            id="route_retraction", rank=1,
            title=f"Send your evidence to {claimant} and ask it to retract the removal request",
            description="A retraction restores the video and clears the strike, without any sworn statement. Attach the same documents this check relied on.",
            step=None, evidence_status=status_for(cn_core_components), sentence_id="route:1"))
        routes.append(Route(
            id="route_counter_notice", rank=2, title="Counter-notice (17 U.S.C. §512(g))",
            description="A sworn legal statement. The claimant then has 10 US business days to show it has filed a lawsuit before the video is restored.",
            step="counter_notice", evidence_status=status_for(cn_all_components), sentence_id="route:2",
            is_chosen_step=(chosen_step == "counter_notice")))
    return routes
