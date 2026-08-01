#include "prl/core/remesh_contract.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <vector>

namespace {

class RecordingSink final : public prl::core::RemeshEventSink {
public:
    void on_remesh(
        const prl::core::RemeshEvent& event,
        const prl::core::SurfaceMeshSnapshot& before,
        const prl::core::SurfaceMeshSnapshot& after
    ) override {
        assert(event.after_revision > event.before_revision);
        assert(before.revision == event.before_revision);
        assert(after.revision == event.after_revision);
        operations.push_back(event.operation);
    }

    std::vector<prl::core::RemeshOperation> operations;
};

} // namespace

int main() {
    using namespace prl::core;

    RecordingSink sink;
    const SurfaceMeshSnapshot before{17, 41, {}, {}};
    const SurfaceMeshSnapshot after{17, 42, {}, {}};
    for (const auto operation : {
             RemeshOperation::edge_split,
             RemeshOperation::edge_swap,
             RemeshOperation::edge_merge,
         }) {
        const RemeshEvent event{17, operation, 41, 42};
        assert(is_valid_remesh_event(event, before, after));
        sink.on_remesh(event, before, after);
    }
    assert(sink.operations.size() == 3);
    assert(!is_valid_remesh_event(
        RemeshEvent{17, RemeshOperation::edge_swap, 42, 42},
        before,
        after
    ));

    const MyocardialMaterialState material{
        701,
        SurfaceRegion::basal,
        {1.0, 0.0, 0.0},
        {0.4, 0.7},
    };
    assert(material.material_point_id == 701);
    assert(material.region == SurfaceRegion::basal);
    assert(material.fiber_direction[0] == 1.0);

    const RemeshTransferAudit audit{
        RemeshOperation::edge_swap,
        1,
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
    };
    assert(audit.region_retention_fraction == 1.0);
    assert(audit.minimum_fiber_alignment == 1.0);
    return 0;
}
