from pitwall.actions import Compound
from pitwall.config import RaceConfig, Rules, TireParameters


def make_config(
    *,
    laps=6,
    pit_loss=10.0,
    degradation=0.0,
    cap=100.0,
    warmup=(),
    min_compounds=2,
    max_stops=2,
    sets=(2, 2, 2),
):
    return RaceConfig(
        name="Hand-calculated synthetic circuit",
        laps=laps,
        base_lap_time_s=100.0,
        pit_loss_s=pit_loss,
        start_compound=Compound.SOFT,
        tires=tuple(
            TireParameters(c, 0.0, degradation, cap, warmup, count)
            for c, count in zip(Compound, sets, strict=True)
        ),
        rules=Rules(max_stops, min_compounds),
    )
