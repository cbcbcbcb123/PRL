#include "prl_cell_engine/cell_surface_force.hpp"

#include "cell.hpp"
#include "node.hpp"
#include "vec3.hpp"

#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

std::shared_ptr<cell> test_cell() {
    mesh cell_mesh;
    cell_mesh.node_pos_lst = {
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    };
    cell_mesh.face_point_ids = {
        {0, 2, 1},
        {0, 1, 3},
        {1, 2, 3},
        {2, 0, 3},
    };
    return std::make_shared<cell>(cell_mesh, 17);
}

bool nearly_equal(const double left, const double right) {
    return std::abs(left - right) <= tolerance;
}

int force_increments_accumulate_by_persistent_vertex_id() {
    auto current_cell = test_cell();
    current_cell->add_force(vec3{0.1, -0.2, 0.3});
    const auto first_id = current_cell->get_node_lst().at(0).get_persistent_id();
    const auto second_id = current_cell->get_node_lst().at(1).get_persistent_id();
    const auto audit = prl::cell_engine::apply_surface_vertex_forces(
        *current_cell,
        0,
        {
            {first_id, {0.4, 0.0, 0.0}},
            {second_id, {-0.4, 0.0, 0.0}},
        }
    );

    require(audit.cell_id == 17 && audit.revision == 0, "force audit identity mismatch");
    require(audit.injected_vertex_count == 2, "force audit count mismatch");
    require(audit.net_force_residual <= tolerance, "force audit resultant mismatch");
    require(audit.net_moment_residual <= tolerance, "force audit moment mismatch");
    const auto& first = current_cell->get_node_lst().at(0).force();
    const auto& second = current_cell->get_node_lst().at(1).force();
    const auto& untouched = current_cell->get_node_lst().at(2).force();
    require(nearly_equal(first.dx(), 0.5) && nearly_equal(first.dy(), -0.2),
            "first persistent vertex did not accumulate its force");
    require(nearly_equal(second.dx(), -0.3) && nearly_equal(second.dy(), -0.2),
            "second persistent vertex did not accumulate its force");
    require(nearly_equal(untouched.dx(), 0.1) && nearly_equal(untouched.dy(), -0.2),
            "force injection changed an unaddressed vertex");
    return 0;
}

int rejected_increments_are_atomic() {
    auto current_cell = test_cell();
    current_cell->add_force(vec3{0.1, -0.2, 0.3});
    const auto valid_id = current_cell->get_node_lst().at(0).get_persistent_id();
    bool unknown_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            0,
            {
                {valid_id, {0.4, 0.0, 0.0}},
                {999999, {0.0, 0.1, 0.0}},
            }
        ));
    } catch(const std::out_of_range&) {
        unknown_rejected = true;
    }
    require(unknown_rejected, "unknown persistent vertex was accepted");

    bool stale_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            1,
            {{valid_id, {0.4, 0.0, 0.0}}}
        ));
    } catch(const std::logic_error&) {
        stale_rejected = true;
    }
    require(stale_rejected, "stale surface-force revision was accepted");

    bool nonfinite_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            0,
            {{valid_id, {std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0}}}
        ));
    } catch(const std::invalid_argument&) {
        nonfinite_rejected = true;
    }
    require(nonfinite_rejected, "non-finite surface-force increment was accepted");
    for(const node& current_node : current_cell->get_node_lst()) {
        require(nearly_equal(current_node.force().dx(), 0.1)
                && nearly_equal(current_node.force().dy(), -0.2)
                && nearly_equal(current_node.force().dz(), 0.3),
                "rejected surface-force injection changed the buffer");
    }
    return 0;
}

int overdamped_step_updates_positions_and_consumes_forces() {
    auto current_cell = test_cell();
    const auto first_id = current_cell->get_node_lst().at(0).get_persistent_id();
    const auto second_id = current_cell->get_node_lst().at(1).get_persistent_id();
    static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
        *current_cell,
        0,
        {
            {first_id, {0.4, 0.0, 0.0}},
            {second_id, {-0.4, 0.0, 0.0}},
        }
    ));
    const auto audit = prl::cell_engine::advance_surface_overdamped(
        *current_cell,
        0,
        0.1,
        2.0
    );

    require(audit.cell_id == 17 && audit.revision == 0,
            "overdamped audit identity mismatch");
    require(audit.stepped_vertex_count == 4, "overdamped audit vertex count mismatch");
    require(nearly_equal(audit.preassembled_force_l2_norm, std::sqrt(0.32)),
            "overdamped preassembled-force norm mismatch");
    require(nearly_equal(audit.additional_force_l2_norm, 0.0),
            "overdamped additional-force norm mismatch");
    require(nearly_equal(audit.total_force_work, 0.016),
            "overdamped force-work mismatch");
    require(nearly_equal(audit.viscous_dissipation, 0.016),
            "overdamped dissipation mismatch");
    require(audit.work_dissipation_residual <= tolerance,
            "overdamped work-dissipation residual mismatch");
    require(audit.net_displacement_residual <= tolerance,
            "balanced overdamped step translated the centroid");
    require(nearly_equal(current_cell->get_node_lst().at(0).pos().dx(), 0.02),
            "first overdamped displacement mismatch");
    require(nearly_equal(current_cell->get_node_lst().at(1).pos().dx(), 0.98),
            "second overdamped displacement mismatch");
    for(const node& current_node : current_cell->get_node_lst()) {
        require(nearly_equal(current_node.force().norm(), 0.0),
                "overdamped step did not reset a force buffer");
    }
    return 0;
}

int rejected_overdamped_step_is_atomic() {
    auto current_cell = test_cell();
    current_cell->add_force(vec3{0.1, -0.2, 0.3});
    const auto before_positions = current_cell->get_node_coord_lst();
    const auto valid_id = current_cell->get_node_lst().at(0).get_persistent_id();

    bool damping_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_surface_overdamped(
            *current_cell,
            0,
            0.1,
            0.0,
            {{valid_id, {0.2, 0.0, 0.0}}}
        ));
    } catch(const std::invalid_argument&) {
        damping_rejected = true;
    }
    require(damping_rejected, "nonpositive overdamped damping was accepted");

    bool unknown_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_surface_overdamped(
            *current_cell,
            0,
            0.1,
            1.0,
            {
                {valid_id, {0.2, 0.0, 0.0}},
                {999999, {0.0, 0.1, 0.0}},
            }
        ));
    } catch(const std::out_of_range&) {
        unknown_rejected = true;
    }
    require(unknown_rejected, "unknown overdamped force vertex was accepted");

    const auto after_positions = current_cell->get_node_coord_lst();
    require(after_positions == before_positions,
            "rejected overdamped step changed a node position");
    for(const node& current_node : current_cell->get_node_lst()) {
        require(nearly_equal(current_node.force().dx(), 0.1)
                && nearly_equal(current_node.force().dy(), -0.2)
                && nearly_equal(current_node.force().dz(), 0.3),
                "rejected overdamped step consumed a force buffer");
    }
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        if(argc != 2) throw std::invalid_argument("one behavior name is required");
        const std::string behavior = argv[1];
        if(behavior == "accumulation") {
            return force_increments_accumulate_by_persistent_vertex_id();
        }
        if(behavior == "failure_atomicity") return rejected_increments_are_atomic();
        if(behavior == "overdamped_step") {
            return overdamped_step_updates_positions_and_consumes_forces();
        }
        if(behavior == "overdamped_failure_atomicity") {
            return rejected_overdamped_step_is_atomic();
        }
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "test_cell_surface_force: " << error.what() << '\n';
        return 1;
    }
}
