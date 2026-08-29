#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
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
    edge_collapse_survivor,
};

enum class RemeshCollapseMode : std::uint8_t {
    none,
    midpoint,
    endpoint_survivor,
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
    RemeshCollapseMode collapse_mode{RemeshCollapseMode::none};
    std::optional<VertexId> survivor_persistent_id{};
    std::vector<VertexId> deleted_persistent_ids{};
    std::optional<VertexId> created_persistent_id{};
};

/** Opaque, cell-scoped authorization for committing one prepared remesh. */
struct RemeshPreparationToken {
    CellId cell_id{};
    MeshRevision before_revision{};
    MeshRevision after_revision{};
    std::uint64_t preparation_id{};
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
 * Legacy on_remesh callbacks are synchronous. Transaction-capable sinks first
 * receive a non-mutating prepare request while the production cell remains at
 * before_revision, followed by exactly one commit or reject. refine_meshes()
 * may transact concurrently for different cells, so shared sinks must be
 * thread-safe and scope pending state per cell.
 */
class RemeshEventSink {
public:
    virtual ~RemeshEventSink() = default;

    virtual void on_remesh(
        const RemeshEvent& event,
        const SurfaceMeshSnapshot& before,
        const SurfaceMeshSnapshot& after
    ) = 0;

    /** Whether this sink implements the non-mutating prepare/commit seam. */
    [[nodiscard]] virtual bool supports_transactional_remesh() const noexcept {
        return false;
    }

    /** Validate and stage a transfer without changing committed sink state. */
    virtual RemeshPreparationToken prepare_remesh(
        const RemeshEvent&,
        const SurfaceMeshSnapshot&,
        const SurfaceMeshSnapshot&
    ) {
        throw std::logic_error("remesh sink does not support transactional prepare");
    }

    /** Commit exactly one previously prepared transfer. */
    virtual void commit_prepared_remesh(const RemeshPreparationToken&) {
        throw std::logic_error("remesh sink does not support transactional commit");
    }

    /** Discard a prepared transfer after a pre-commit failure. */
    virtual void reject_prepared_remesh(
        const RemeshPreparationToken&
    ) noexcept {}
};

} // namespace prl::core
