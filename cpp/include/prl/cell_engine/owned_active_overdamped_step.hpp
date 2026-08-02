#pragma once

#include "prl/cell_engine/active_overdamped_step.hpp"

#include <array>
#include <cstddef>
#include <memory>
#include <vector>

class cell;
class contact_face_face_via_coupling;

namespace prl::cell_engine {

/** Ledger for one PRL-owned passive/contact/active overdamped cell step. */
struct OwnedActiveCellOverdampedStepAudit {
    ActiveCellOverdampedStepAudit motion{};
    std::size_t contact_context_cell_count{};
    bool contact_assembly_executed{};
    double contact_target_force_l2_norm{};
    double contact_context_net_force_residual{};
    double contact_context_net_moment_residual{};
    double passive_force_increment_l2_norm{};
    double preactive_force_l2_norm{};
    double surface_area_after{};
    double volume_after{};
    std::array<double, 3> centroid_after{};
    double minimum_face_area_after{};
};

/**
 * Execute one owned cell step with real passive assembly and cache refresh.
 *
 * The frozen X1-H contact path accepts the real face-face contact kernel only,
 * with one mobile target and force-only static contact bodies.
 */
[[nodiscard]] OwnedActiveCellOverdampedStepAudit
advance_owned_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    double time_step,
    CellSurfaceDampingLaw damping,
    ::contact_face_face_via_coupling* contact_model = nullptr,
    const std::vector<std::shared_ptr<::cell>>& contact_context = {}
);

/** Replay-compatible X1-H overload using uniform per-vertex damping. */
[[nodiscard]] OwnedActiveCellOverdampedStepAudit
advance_owned_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    double time_step,
    double damping_coefficient,
    ::contact_face_face_via_coupling* contact_model = nullptr,
    const std::vector<std::shared_ptr<::cell>>& contact_context = {}
);

} // namespace prl::cell_engine
