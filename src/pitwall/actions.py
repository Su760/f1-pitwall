"""Public action vocabulary; enum order also defines inventory and mask order."""

from enum import StrEnum


class Compound(StrEnum):
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"


class Action(StrEnum):
    STAY_OUT = "stay_out"
    PIT_SOFT = "pit_soft"
    PIT_MEDIUM = "pit_medium"
    PIT_HARD = "pit_hard"

    @property
    def compound(self) -> Compound | None:
        return None if self is Action.STAY_OUT else Compound(self.value.removeprefix("pit_"))

    @classmethod
    def pit(cls, compound: Compound) -> "Action":
        return cls(f"pit_{compound.value}")
