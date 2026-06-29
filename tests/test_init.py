from arrow import ButtonId, OtherId, RoutineId


def test_no_duplicate_key_positions():
    positions = [bid.value for bid in ButtonId] + [rid.value for rid in RoutineId] + [oid.value for oid in OtherId]
    assert len(positions) == len(set(positions))
