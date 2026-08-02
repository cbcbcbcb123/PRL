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

/** Audit of one atomic overdamped position update. */
struct SurfaceOverdampedStepAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t stepped_vertex_count{};
    double time_step{};
    double damping_coefficient{};
    double preassembled_force_l2_norm{};
    double additional_force_l2_norm{};
    double total_force_l2_norm{};
    double displacement_l2_norm{};
    double total_force_work{};
    double viscous_dissipation{};
    double work_dissipation_residual{};
    double net_displacement_residual{};
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

/**
 * Advance one non-static cell by dx = dt * force / damping and reset forces.
 *
 * Existing node forces are treated as preassembled contributions. Additional
 * forces are addressed by persistent vertex ID. Positions and force buffers
 * are committed only after the complete step has been validated.
 */
[[nodiscard]] SurfaceOverdampedStepAudit advance_surface_overdamped(
    ::cell& target,
    core::MeshRevision expected_revision,
    double time_step,
    double damping_coefficient,
    const std::vector<SurfaceVertexForce>& additional_forces = {}
);

} // namespace prl::cell_engine
