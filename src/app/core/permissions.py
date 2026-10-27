"""
Shared permission rules.

Keeping them in one place avoids the classic bug where one endpoint checks
ownership and a sibling one forgets to.
"""

from app.models.gym import Gym
from app.models.user import User


def can_edit_gym(user: User, gym: Gym) -> bool:
    """Whether ``user`` may change a gym (and its grades).

    Unverified gyms are open to any authenticated user, so a mistake made when
    creating one can be fixed right away. Verified gyms are locked to admins.
    """
    if user.is_admin:
        return True
    return not gym.is_verified


def can_delete_gym(user: User) -> bool:
    """Deleting a gym cascades to sessions, ascents and competitions."""
    return bool(user.is_admin)
