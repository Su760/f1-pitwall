"""Bounded exhaustive fixed-schedule search, scored only by the race engine.

Candidate counts include illegal schedules. Each stop count uses every increasing
boundary combination and every compound product, including same-compound fresh
sets. The engine's action mask and terminal checks determine the legal subset.
Only a fully evaluated search returns an OptimizationResult; unsupported sizes
and interruptions never return a partial result labelled exhaustive.
"""

import heapq
from dataclasses import dataclass
from itertools import combinations, product

from pitwall.actions import Compound
from pitwall.config import RaceConfig, integer
from pitwall.engine import InvalidAction, simulate
from pitwall.policies import FixedSchedule, PitStop
from pitwall.results import RaceResult


class SearchTooLarge(ValueError):
    """The entire requested candidate space exceeds explicit operational limits."""


@dataclass(frozen=True)
class SearchLimits:
    """Operational search budgets, unrelated to physical/model parameters.

    The lap budget conservatively assumes every candidate runs every lap, even
    though an illegal action may reject a candidate earlier. Raise these explicit
    settings only when the caller accepts the additional computation and memory.
    """

    max_candidates: int = 100_000
    max_lap_evaluations: int = 2_000_000

    def __post_init__(self) -> None:
        integer(self.max_candidates, "max_candidates", 1)
        integer(self.max_lap_evaluations, "max_lap_evaluations", 1)


@dataclass(frozen=True)
class RankedStrategy:
    schedule: FixedSchedule
    result: RaceResult
    gap_s: float


@dataclass(frozen=True)
class OptimizationResult:
    candidate_count: int
    legal_count: int
    candidate_counts_by_stops: tuple[int, ...]
    legal_counts_by_stops: tuple[int, ...]
    max_lap_evaluations_required: int
    search_complete: bool
    ranked: tuple[RankedStrategy, ...]

    @property
    def best(self) -> RankedStrategy:
        return self.ranked[0]


def _preflight(config: RaceConfig, limits: SearchLimits) -> tuple[int, ...]:
    boundaries = config.laps - 1
    maximum_stops = min(config.rules.max_pit_stops, boundaries)
    counts = []
    count = 1
    total = 0
    for stops in range(maximum_stops + 1):
        # C(n, k)*3**k from its preceding term; stop counting immediately if
        # unsupported, without materializing huge products or boundary pools.
        if stops:
            count = count * (boundaries - stops + 1) * len(Compound) // stops
        counts.append(count)
        total += count
        if total > limits.max_candidates:
            raise SearchTooLarge(
                f"Exhaustive search unsupported: at least {total} candidates exceed "
                f"max_candidates={limits.max_candidates}; no candidates evaluated"
            )
        if total * config.laps > limits.max_lap_evaluations:
            raise SearchTooLarge(
                f"Exhaustive search unsupported: at least {total * config.laps} potential "
                f"lap evaluations exceed max_lap_evaluations={limits.max_lap_evaluations}; "
                "no candidates evaluated"
            )
    return tuple(counts)


def optimize(config: RaceConfig, *, limits: SearchLimits, top_k: int = 5) -> OptimizationResult:
    """Return an exact reference optimum for the configured starting compound.

    Ties use full-precision elapsed time, then fewest stops, lexicographically
    increasing boundary tuples, and compound declaration order (soft, medium,
    hard). Close but unequal times are never collapsed with a tolerance.

    ``top_k`` controls retained alternatives only, never the search space; fewer
    rows are returned when fewer legal schedules exist. The caller supplies
    explicit SearchLimits (or intentionally chooses their documented defaults).
    KeyboardInterrupt and unexpected engine errors propagate without a result.
    """
    if not isinstance(config, RaceConfig):
        raise ValueError("config must be a RaceConfig")
    if not isinstance(limits, SearchLimits):
        raise ValueError("limits must be SearchLimits")
    integer(top_k, "top_k", 1)
    candidate_counts = _preflight(config, limits)
    legal_counts = [0] * len(candidate_counts)
    candidate_count = 0
    compound_order = {compound: index for index, compound in enumerate(Compound)}
    # Negated ranking fields put the worst retained candidate at the heap root.
    # Each schedule has a unique boundary/compound key, so result objects are
    # never compared even when times tie. Memory is bounded by min(top_k, legal).
    retained: list[
        tuple[
            tuple[float, int, tuple[int, ...], tuple[int, ...]],
            FixedSchedule,
            RaceResult,
        ]
    ] = []
    for stops in range(len(candidate_counts)):
        for boundaries in combinations(range(1, config.laps), stops):
            for compounds in product(Compound, repeat=stops):
                pit_stops = tuple(
                    PitStop(boundary, compound)
                    for boundary, compound in zip(boundaries, compounds, strict=True)
                )
                name = "optimized-" + (
                    "-".join(f"{s.after_lap}-{s.compound.value}" for s in pit_stops) or "no-stops"
                )
                schedule = FixedSchedule(name, pit_stops)
                candidate_count += 1
                try:
                    result = simulate(config, schedule)
                except InvalidAction:
                    continue
                if not result.legal:
                    continue
                legal_counts[stops] += 1
                reverse_key = (
                    -result.total_elapsed_s,
                    -stops,
                    tuple(-boundary for boundary in boundaries),
                    tuple(-compound_order[compound] for compound in compounds),
                )
                entry = (reverse_key, schedule, result)
                if len(retained) < top_k:
                    heapq.heappush(retained, entry)
                elif reverse_key > retained[0][0]:
                    heapq.heapreplace(retained, entry)

    if candidate_count != sum(candidate_counts):
        raise RuntimeError("Search enumeration did not match preflight; no exhaustive result")
    if not retained:
        raise RuntimeError("Validated configuration produced no legal schedule")
    retained.sort(key=lambda entry: entry[0], reverse=True)
    best_time = retained[0][2].total_elapsed_s
    ranked = tuple(
        RankedStrategy(schedule, result, result.total_elapsed_s - best_time)
        for _, schedule, result in retained
    )
    return OptimizationResult(
        candidate_count,
        sum(legal_counts),
        candidate_counts,
        tuple(legal_counts),
        candidate_count * config.laps,
        True,
        ranked,
    )
