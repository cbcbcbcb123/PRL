#pragma once

#include "prl_cell_engine/remesh_contract.hpp"

#include <array>
#include <cstddef>
#include <vector>

class cell;

namespace prl::cell_engine {

/** One additive force addressed by stable surface-vertex identity. */
struct SurfaceVertexForce {
    core::VertexId vertex_id{};
    std::array<double, 3> force{};
};

/** Audit of the force increment committed to one cell force buffer. */
struct SurfaceForceInjectionAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t injected_vertex_count{};
    double injected_force_l2_norm{};
    double net_force_residual{};
    double net_moment_residual{};
};

/**
 * Atomically accumulate finite force increments into used cell vertices.
 *
 * The caller must own the target cell for the duration of this operation.
 * All IDs, the expected topology revision, and all resulting force values are
 * validated before the first force-buffer write.
 */
[[nodiscard]] SurfaceForceInjectionAudit apply_surface_vertex_forces(
    ::cell& target,
    core::MeshRevision expected_revision,
    const std::vector<SurfaceVertexForce>& forces
);

} // namespace prl::cell_engine
