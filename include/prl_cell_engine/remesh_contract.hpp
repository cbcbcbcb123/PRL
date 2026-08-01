#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace prl::core {

using CellId = std::uint64_t;
using MaterialPointId = std::uint64_t;
using MeshRevision = std::uint64_t;
using VertexId = std::uint64_t;

enum class RemeshOperation : std::uint8_t {
    edge_split,
    edge_swap,
    edge_merge,
};

enum class SurfaceRegion : std::uint8_t {
    apical,
    basal,
    lateral,
};

struct SurfaceVertex {
    VertexId persistent_id{};
    std::array<double, 3> position{};
};

struct SurfaceFace {
    std::array<std::uint32_t, 3> vertex_indices{};
};

struct SurfaceMeshSnapshot {
    CellId cell_id{};
    MeshRevision revision{};
    std::vector<SurfaceVertex> vertices{};
    std::vector<SurfaceFace> faces{};
};

struct RemeshEvent {
    CellId cell_id{};
    RemeshOperation operation{};
    MeshRevision before_revision{};
    MeshRevision after_revision{};
};

[[nodiscard]] constexpr bool is_valid_remesh_event(
    const RemeshEvent& event,
    const SurfaceMeshSnapshot& before,
    const SurfaceMeshSnapshot& after
) noexcept {
    return event.cell_id == before.cell_id
        && event.cell_id == after.cell_id
        && event.before_revision == before.revision
        && event.after_revision == after.revision
        && event.after_revision > event.before_revision;
}

struct MyocardialMaterialState {
    MaterialPointId material_point_id{};
    SurfaceRegion region{};
    std::array<double, 3> fiber_direction{};
    std::vector<double> active_state{};
};

struct RemeshTransferAudit {
    RemeshOperation operation{};
    std::size_t point_count{};
    double region_retention_fraction{};
    double active_state_residual{};
    double maximum_fiber_norm_error{};
    double maximum_fiber_tangency_error{};
    double minimum_fiber_alignment{};
    double maximum_rebind_error{};
    double id_retention_fraction{};
    double reference_weight_residual{};
};

/**
 * Stable observer seam between the cell engine and PRL material-state owner.
 *
 * A callback is synchronous and occurs after one accepted topology operation,
 * before another operation may mutate the same cell. refine_meshes() may invoke
 * callbacks concurrently for different cells, so shared sinks must be
 * thread-safe. No callback occurs when an operation is rejected before mutation.
 */
class RemeshEventSink {
public:
    virtual ~RemeshEventSink() = default;

    virtual void on_remesh(
        const RemeshEvent& event,
        const SurfaceMeshSnapshot& before,
        const SurfaceMeshSnapshot& after
    ) = 0;
};

} // namespace prl::core
