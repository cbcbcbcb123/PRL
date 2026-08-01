#pragma once

#include "prl/core/remesh_contract.hpp"

#include <array>
#include <cstdint>
#include <memory>
#include <vector>

namespace prl::core {

/**
 * One persistent myocardial material point and its current geometric host.
 *
 * Biology is owned by material_point_id. The host is expressed using stable
 * vertex IDs, never a temporary face index; barycentric coordinates follow the
 * same vertex order as host_vertex_ids.
 */
struct SurfaceMaterialPoint {
    MyocardialMaterialState material{};
    std::array<VertexId, 3> host_vertex_ids{};
    std::array<double, 3> barycentric{};
    double reference_weight{};
};

struct MyocardialCellMaterialState {
    CellId cell_id{};
    MeshRevision revision{};
    std::vector<SurfaceMaterialPoint> points{};
};

/**
 * Thread-safe production consumer for synchronous cell-engine remesh events.
 *
 * Each cell is transferred atomically under its own lock. Events for different
 * cells may proceed concurrently. A failed transfer leaves the registered
 * state and revision unchanged.
 */
class MyocardialMaterialTransferSink final : public RemeshEventSink {
public:
    explicit MyocardialMaterialTransferSink(double maximum_rebind_distance = 1.0e-12);
    ~MyocardialMaterialTransferSink() override;

    MyocardialMaterialTransferSink(const MyocardialMaterialTransferSink&) = delete;
    MyocardialMaterialTransferSink& operator=(const MyocardialMaterialTransferSink&) = delete;
    MyocardialMaterialTransferSink(MyocardialMaterialTransferSink&&) = delete;
    MyocardialMaterialTransferSink& operator=(MyocardialMaterialTransferSink&&) = delete;

    void register_cell(
        const SurfaceMeshSnapshot& mesh,
        std::vector<SurfaceMaterialPoint> points
    );

    void on_remesh(
        const RemeshEvent& event,
        const SurfaceMeshSnapshot& before,
        const SurfaceMeshSnapshot& after
    ) override;

    [[nodiscard]] MyocardialCellMaterialState cell_state(CellId cell_id) const;
    [[nodiscard]] RemeshTransferAudit last_audit(CellId cell_id) const;

private:
    class Impl;
    std::unique_ptr<Impl> implementation_;
};

} // namespace prl::core
