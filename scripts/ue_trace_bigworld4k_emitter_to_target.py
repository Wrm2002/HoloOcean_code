"""Trace from the BigWorld4K sonar emitter to the primary smoke target."""

import unreal


MAP_PATH = "/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609"
EMITTER_LABEL = "WRM4K_SonarDatasetEmitter_Smoke01"
TARGET_LABEL = "WRM4K_Target_Class3_Rock_Block"


def find_actor(label):
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    raise RuntimeError("missing actor {}".format(label))


unreal.log("WRM4K_TRACE_BEGIN")
if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
    raise RuntimeError("failed to load {}".format(MAP_PATH))

emitter = find_actor(EMITTER_LABEL)
target = find_actor(TARGET_LABEL)
start = emitter.get_actor_location() + emitter.get_actor_forward_vector() * 120.0 + unreal.Vector(0.0, 0.0, 60.0)
end = target.get_actor_location()

for query_name in [name for name in dir(unreal.TraceTypeQuery) if name.startswith("TRACE_TYPE_QUERY")][:8]:
    query = getattr(unreal.TraceTypeQuery, query_name)
    hit = unreal.SystemLibrary.line_trace_single(
        emitter,
        start,
        end,
        query,
        False,
        [emitter],
        unreal.DrawDebugTrace.NONE,
        True,
    )
    blocking_hit = bool(getattr(hit, "blocking_hit", getattr(hit, "b_blocking_hit", False)))
    hit_actor = getattr(hit, "hit_actor", getattr(hit, "actor", None))
    hit_label = hit_actor.get_actor_label() if hit_actor else "None"
    hit_loc = getattr(hit, "location", getattr(hit, "impact_point", unreal.Vector()))
    unreal.log(
        "WRM4K_TRACE_RESULT query={} blocking={} hit_actor={} hit_loc=({:.1f},{:.1f},{:.1f}) start=({:.1f},{:.1f},{:.1f}) end=({:.1f},{:.1f},{:.1f})".format(
            query_name,
            blocking_hit,
            hit_label,
            hit_loc.x,
            hit_loc.y,
            hit_loc.z,
            start.x,
            start.y,
            start.z,
            end.x,
            end.y,
            end.z,
        )
    )
unreal.log("WRM4K_TRACE_DONE")
