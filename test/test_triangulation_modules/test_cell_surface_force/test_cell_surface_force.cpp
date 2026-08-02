#include "prl_cell_engine/cell_surface_force.hpp"

#include "cell.hpp"
#include "face.hpp"
#include "node.hpp"
#include "vec3.hpp"

#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

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

mesh cube_surface_mesh() {
    mesh result;
    result.node_pos_lst = {
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        1.0, 1.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
        1.0, 0.0, 1.0,
        1.0, 1.0, 1.0,
        0.0, 1.0, 1.0,
    };
    result.face_point_ids = {
        {0, 2, 1}, {0, 3, 2},
        {4, 5, 6}, {4, 6, 7},
        {0, 1, 5}, {0, 5, 4},
        {3, 7, 6}, {3, 6, 2},
        {0, 4, 7}, {0, 7, 3},
        {1, 2, 6}, {1, 6, 5},
    };
    return result;
}

mesh centroid_refined(const mesh& input) {
    mesh result;
    result.node_pos_lst = input.node_pos_lst;
    result.face_point_ids.reserve(input.face_point_ids.size() * 3);
    for(const auto& triangle : input.face_point_ids) {
        const unsigned centroid_id = static_cast<unsigned>(result.node_pos_lst.size() / 3);
        for(std::size_t component = 0; component < 3; ++component) {
            result.node_pos_lst.push_back(
                (input.node_pos_lst.at(3 * triangle[0] + component)
                 + input.node_pos_lst.at(3 * triangle[1] + component)
                 + input.node_pos_lst.at(3 * triangle[2] + component)) / 3.0
            );
        }
        result.face_point_ids.push_back({triangle[0], triangle[1], centroid_id});
        result.face_point_ids.push_back({triangle[1], triangle[2], centroid_id});
        result.face_point_ids.push_back({triangle[2], triangle[0], centroid_id});
    }
    return result;
}

std::vector<double> independent_barycentric_dual_areas(const cell& target) {
    std::vector<double> result(target.get_node_lst().size(), 0.0);
    for(const face& current_face : target.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        const auto& a = target.get_node_lst().at(ids[0]).pos();
        const auto& b = target.get_node_lst().at(ids[1]).pos();
        const auto& c = target.get_node_lst().at(ids[2]).pos();
        const std::array<double, 3> ab{
            b.dx() - a.dx(), b.dy() - a.dy(), b.dz() - a.dz(),
        };
        const std::array<double, 3> ac{
            c.dx() - a.dx(), c.dy() - a.dy(), c.dz() - a.dz(),
        };
        const std::array<double, 3> cross{
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        };
        const double area = 0.5 * std::sqrt(
            cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]
        );
        for(const unsigned id : ids) result.at(id) += area / 3.0;
    }
    return result;
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
    require(audit.refreshed_face_count == 4,
            "overdamped step did not refresh every face");
    require(audit.surface_area_after > 0.0
            && audit.volume_after > 0.0
            && audit.minimum_face_area_after > 0.0,
            "overdamped geometry audit is invalid");
    require(nearly_equal(current_cell->get_area(), audit.surface_area_after)
            && nearly_equal(current_cell->get_volume(), audit.volume_after),
            "overdamped step left stale cell geometry caches");
    require(nearly_equal(current_cell->get_centroid().dx(), audit.centroid_after[0])
            && nearly_equal(current_cell->get_centroid().dy(), audit.centroid_after[1])
            && nearly_equal(current_cell->get_centroid().dz(), audit.centroid_after[2]),
            "overdamped step left a stale centroid cache");
    double cached_face_area = 0.0;
    for(const face& current_face : current_cell->get_face_lst()) {
        if(!current_face.is_used()) continue;
        cached_face_area += current_face.get_area();
    }
    require(nearly_equal(cached_face_area, audit.surface_area_after),
            "overdamped step left stale face-area caches");
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(std::isfinite(current_node.get_curvature())
                && nearly_equal(current_node.get_normal().norm(), 1.0),
                "overdamped step left stale node geometry caches");
    }
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

int geometry_rejection_preserves_positions_and_forces() {
    auto current_cell = test_cell();
    const auto moving_id = current_cell->get_node_lst().at(1).get_persistent_id();
    static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
        *current_cell,
        0,
        {{moving_id, {-10.0, 0.0, 0.0}}}
    ));
    const auto before_positions = current_cell->get_node_coord_lst();

    bool invalid_geometry_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_surface_overdamped(
            *current_cell,
            0,
            0.1,
            1.0
        ));
    } catch(const std::runtime_error&) {
        invalid_geometry_rejected = true;
    }
    require(invalid_geometry_rejected,
            "overdamped step accepted a collapsed surface");
    require(current_cell->get_node_coord_lst() == before_positions,
            "geometry rejection committed a node position");
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        const double expected_x = current_node.get_persistent_id() == moving_id
            ? -10.0
            : 0.0;
        require(nearly_equal(current_node.force().dx(), expected_x)
                && nearly_equal(current_node.force().dy(), 0.0)
                && nearly_equal(current_node.force().dz(), 0.0),
                "geometry rejection changed or consumed a force buffer");
    }
    return 0;
}

int dual_area_damping_is_spatially_consistent() {
    constexpr double time_step = 0.1;
    constexpr double damping_per_area = 2.0;
    constexpr std::array<double, 3> traction{0.4, -0.2, 0.1};
    const std::array<double, 3> expected_displacement{
        time_step * traction[0] / damping_per_area,
        time_step * traction[1] / damping_per_area,
        time_step * traction[2] / damping_per_area,
    };

    std::array<mesh, 3> refinements;
    refinements[0] = cube_surface_mesh();
    refinements[1] = centroid_refined(refinements[0]);
    refinements[2] = centroid_refined(refinements[1]);
    const std::array<std::size_t, 3> expected_vertex_counts{8, 20, 56};

    for(std::size_t level = 0; level < refinements.size(); ++level) {
        auto current_cell = std::make_shared<cell>(refinements[level], 100 + level);
        const auto before_positions = current_cell->get_node_coord_lst();
        const auto dual_areas = independent_barycentric_dual_areas(*current_cell);
        std::vector<prl::cell_engine::SurfaceVertexForce> surface_traction;
        surface_traction.reserve(current_cell->get_nb_of_nodes());
        for(std::size_t index = 0; index < current_cell->get_node_lst().size(); ++index) {
            const node& current_node = current_cell->get_node_lst().at(index);
            if(!current_node.is_used()) continue;
            surface_traction.push_back({
                current_node.get_persistent_id(),
                {
                    dual_areas.at(index) * traction[0],
                    dual_areas.at(index) * traction[1],
                    dual_areas.at(index) * traction[2],
                },
            });
        }
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            0,
            surface_traction
        ));
        const prl::cell_engine::SurfaceDampingLaw damping{
            prl::cell_engine::SurfaceDampingMeasure::barycentric_dual_area,
            damping_per_area,
        };
        const auto audit = prl::cell_engine::advance_surface_overdamped(
            *current_cell,
            0,
            time_step,
            damping
        );

        std::cout << std::setprecision(17)
                  << "level=" << level
                  << " vertices=" << audit.stepped_vertex_count
                  << " control_area_sum=" << audit.control_area_sum
                  << " min_nodal_damping=" << audit.minimum_nodal_damping
                  << " max_nodal_damping=" << audit.maximum_nodal_damping
                  << " displacement_l2=" << audit.displacement_l2_norm
                  << " force_work=" << audit.total_force_work
                  << " viscous_dissipation=" << audit.viscous_dissipation
                  << '\n';

        require(audit.stepped_vertex_count == expected_vertex_counts[level],
                "refinement level has an unexpected vertex count");
        require(audit.damping_measure
                    == prl::cell_engine::SurfaceDampingMeasure::barycentric_dual_area,
                "overdamped audit lost the dual-area damping measure");
        require(nearly_equal(audit.control_area_sum, 6.0),
                "dual control areas do not partition the cube surface");
        require(audit.minimum_nodal_damping > 0.0
                    && audit.maximum_nodal_damping >= audit.minimum_nodal_damping,
                "effective dual-area nodal damping is invalid");
        for(std::size_t index = 0; index < current_cell->get_node_lst().size(); ++index) {
            const node& current_node = current_cell->get_node_lst().at(index);
            if(!current_node.is_used()) continue;
            const auto& before = before_positions.at(index);
            require(nearly_equal(current_node.pos().dx() - before.at(0),
                                 expected_displacement[0])
                        && nearly_equal(current_node.pos().dy() - before.at(1),
                                        expected_displacement[1])
                        && nearly_equal(current_node.pos().dz() - before.at(2),
                                        expected_displacement[2]),
                    "dual-area manufactured traction changed with mesh refinement");
        }
        require(audit.work_dissipation_residual <= tolerance,
                "dual-area force work and dissipation diverged");
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
        if(behavior == "overdamped_geometry_atomicity") {
            return geometry_rejection_preserves_positions_and_forces();
        }
        if(behavior == "dual_area_spatial_consistency") {
            return dual_area_damping_is_spatially_consistent();
        }
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "test_cell_surface_force: " << error.what() << '\n';
        return 1;
    }
}
