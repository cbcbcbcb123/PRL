#include "prl/cell_engine/owned_active_overdamped_step.hpp"
#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "contact_face_face_via_coupling.hpp"
#include "custom_structures.hpp"
#include "face.hpp"
#include "node.hpp"
#include "static_cell.hpp"

#include <algorithm>
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

constexpr double tolerance = 1.0e-10;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

bool nearly_equal(const double left, const double right) {
    return std::abs(left - right) <= tolerance;
}

std::shared_ptr<cell_type_parameters> passive_cell_type() {
    face_type_parameters face_type;
    face_type.name_ = "myocardial_surface";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = 0.2;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 1.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "myocardial_test";
    result->global_type_id_ = 2;
    result->mass_density_ = 1.0;
    result->bulk_modulus_ = 0.0;
    result->max_pressure_ = 1.0e6;
    result->initial_pressure_ = 0.0;
    result->area_elasticity_modulus_ = 0.0;
    result->avg_division_vol_ = 1.0e6;
    result->std_division_vol_ = 0.0;
    result->avg_growth_rate_ = 0.0;
    result->std_growth_rate_ = 0.0;
    result->min_vol_ = 1.0e-12;
    result->angle_regularization_factor_ = 0.0;
    result->target_isoperimetric_ratio_ = 150.0;
    result->surface_coupling_max_curvature_ = 1.0e6;
    result->add_face_type(face_type);
    return result;
}

cell_ptr passive_active_test_cell() {
    mesh cell_mesh;
    cell_mesh.node_pos_lst = {
         0.0,  0.0,  0.0,
         0.0, -3.0,  0.0,
        -1.0, -1.5,  0.0,
         1.0, -1.5,  0.0,
         0.0,  0.0, -1.0,
         0.0, -3.0, -1.0,
        -1.0, -1.5, -1.0,
         1.0, -1.5, -1.0,
    };
    cell_mesh.face_point_ids = {
        {0, 1, 2}, {0, 1, 3}, {0, 4, 2}, {2, 6, 4},
        {2, 6, 5}, {5, 1, 2}, {0, 3, 7}, {7, 4, 0},
        {3, 1, 5}, {5, 7, 3}, {4, 5, 6}, {4, 5, 7},
    };
    auto result = std::make_shared<cell>(cell_mesh, 17, passive_cell_type());
    result->initialize_cell_properties();
    return result;
}

cell_ptr static_contact_body() {
    auto body_type = passive_cell_type();
    body_type->name_ = "static_contact_body";
    body_type->global_type_id_ = 1;
    body_type->face_types_.at(0).surface_tension_ = 0.0;
    body_type->face_types_.at(0).repulsion_strength_ = 5.0;

    mesh body_mesh;
    body_mesh.node_pos_lst = {
        -2.0, -4.0, -0.4,
         2.0, -4.0, -0.4,
         2.0,  1.0, -0.4,
        -2.0,  1.0, -0.4,
        -2.0, -4.0,  0.1,
         2.0, -4.0,  0.1,
         2.0,  1.0,  0.1,
        -2.0,  1.0,  0.1,
    };
    body_mesh.face_point_ids = {
        {0, 2, 1}, {0, 3, 2},
        {4, 5, 6}, {4, 6, 7},
        {0, 1, 5}, {0, 5, 4},
        {3, 7, 6}, {3, 6, 2},
        {0, 4, 7}, {0, 7, 3},
        {1, 2, 6}, {1, 6, 5},
    };
    auto result = std::make_shared<static_cell>(body_mesh, 29, body_type);
    result->initialize_cell_properties();
    return result;
}

global_simulation_parameters contact_parameters() {
    global_simulation_parameters result;
    result.damping_coefficient_ = 10.0;
    result.simulation_duration_ = 1.0;
    result.sampling_period_ = 1.0;
    result.time_step_ = 1.0e-3;
    result.min_edge_len_ = 0.117;
    result.contact_cutoff_adhesion_ = 0.45;
    result.contact_cutoff_repulsion_ = 0.45;
    return result;
}

prl::core::VertexId persistent_node_id(const cell& current_cell, const unsigned local_id) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

std::vector<prl::core::SurfaceMaterialPoint> active_material_points(
    const cell& current_cell
) {
    using namespace prl::core;
    const auto activation = c1_activation_protocol(2.5, 0.0, 0.1);
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        {
            MyocardialMaterialState{
                101,
                SurfaceRegion::apical,
                {1.0, 0.0, 0.0},
                {activation.activation, activation.activation_rate},
            },
            {a, b, c},
            {0.2, 0.3, 0.5},
            0.17,
        },
        {
            MyocardialMaterialState{
                205,
                SurfaceRegion::basal,
                {1.0, 0.0, 0.0},
                {},
            },
            {a, b, d},
            {0.4, 0.25, 0.35},
            0.23,
        },
    };
}

struct IndependentGeometry {
    double area{};
    double volume{};
    std::array<double, 3> centroid{};
    double minimum_face_area{};
};

IndependentGeometry independent_geometry(const prl::core::SurfaceMeshSnapshot& mesh) {
    IndependentGeometry result;
    result.minimum_face_area = std::numeric_limits<double>::infinity();
    double signed_six_volume = 0.0;
    for(const auto& face_data : mesh.faces) {
        const auto& a = mesh.vertices.at(face_data.vertex_indices[0]).position;
        const auto& b = mesh.vertices.at(face_data.vertex_indices[1]).position;
        const auto& c = mesh.vertices.at(face_data.vertex_indices[2]).position;
        const std::array<double, 3> ab{b[0] - a[0], b[1] - a[1], b[2] - a[2]};
        const std::array<double, 3> ac{c[0] - a[0], c[1] - a[1], c[2] - a[2]};
        const std::array<double, 3> cross{
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        };
        const double face_area = 0.5 * std::sqrt(
            cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]
        );
        result.area += face_area;
        result.minimum_face_area = std::min(result.minimum_face_area, face_area);
        for(std::size_t component = 0; component < 3; ++component) {
            result.centroid[component] += face_area
                * (a[component] + b[component] + c[component]) / 3.0;
        }
        signed_six_volume += a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]);
    }
    for(double& component : result.centroid) component /= result.area;
    result.volume = std::abs(signed_six_volume) / 6.0;
    return result;
}

int real_passive_active_step_refreshes_geometry() {
    using namespace prl::core;
    auto current_cell = passive_active_test_cell();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell),
    };
    const auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );

    const auto audit = prl::cell_engine::advance_owned_active_cell_overdamped_one_step(
        *current_cell,
        material,
        {unit},
        1.0e-3,
        10.0
    );
    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto expected_geometry = independent_geometry(after_mesh);

    require(audit.motion.cell_id == 17 && audit.motion.revision == 0,
            "owned-step audit identity mismatch");
    require(!audit.contact_assembly_executed,
            "contact assembly ran without a contact context");
    require(audit.passive_force_increment_l2_norm > 0.0,
            "real cell::apply_internal_forces produced no passive force");
    require(audit.motion.active_force_l2_norm > 0.0,
            "owned step omitted active force assembly");
    require(audit.motion.preassembled_force_l2_norm > 0.0,
            "owned step did not pass passive force into the motion primitive");
    require(nearly_equal(audit.surface_area_after, expected_geometry.area),
            "owned-step area audit disagrees with independent geometry");
    require(nearly_equal(audit.volume_after, expected_geometry.volume),
            "owned-step volume audit disagrees with independent geometry");
    require(nearly_equal(audit.minimum_face_area_after, expected_geometry.minimum_face_area),
            "owned-step minimum-face-area audit mismatch");
    require(nearly_equal(current_cell->get_area(), expected_geometry.area),
            "cell area cache was not refreshed after motion");
    require(nearly_equal(current_cell->get_volume(), expected_geometry.volume),
            "cell volume cache was not refreshed after motion");
    for(std::size_t component = 0; component < 3; ++component) {
        require(nearly_equal(audit.centroid_after[component], expected_geometry.centroid[component]),
                "owned-step centroid audit mismatch");
    }
    require(nearly_equal(current_cell->get_centroid().dx(), expected_geometry.centroid[0])
            && nearly_equal(current_cell->get_centroid().dy(), expected_geometry.centroid[1])
            && nearly_equal(current_cell->get_centroid().dz(), expected_geometry.centroid[2]),
            "cell centroid cache was not refreshed after motion");
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "owned step did not consume the final force buffer");
    }
    return 0;
}

int real_contact_force_enters_the_owned_step() {
    using namespace prl::core;
    auto current_cell = passive_active_test_cell();
    auto contact_body = static_contact_body();
    current_cell->set_local_id(0);
    contact_body->set_local_id(1);
    const auto body_positions_before = contact_body->get_node_coord_lst();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell),
    };
    const auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    contact_face_face_via_coupling contact_model(contact_parameters());

    const auto audit = prl::cell_engine::advance_owned_active_cell_overdamped_one_step(
        *current_cell,
        material,
        {unit},
        1.0e-3,
        10.0,
        &contact_model,
        {current_cell, contact_body}
    );

    require(audit.contact_assembly_executed,
            "real contact model was not invoked by the owned step");
    require(audit.contact_context_cell_count == 2,
            "owned contact-context count mismatch");
    require(audit.contact_target_force_l2_norm > 0.0,
            "real contact model produced no target-cell force");
    require(audit.contact_context_net_force_residual <= tolerance,
            "real contact model violated action-reaction force balance");
    require(audit.contact_context_net_moment_residual <= tolerance,
            "real contact model violated action-reaction moment balance");
    require(audit.motion.preassembled_force_l2_norm > 0.0,
            "contact/passive forces did not reach the motion primitive");
    require(contact_body->get_node_coord_lst() == body_positions_before,
            "force-only static contact body moved during the owned step");
    for(const node& current_node : contact_body->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "owned step left a force buffer on the static contact body");
    }
    return 0;
}

int post_assembly_failure_cleans_force_buffers_without_motion() {
    using namespace prl::core;
    auto current_cell = passive_active_test_cell();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell),
    };
    auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    material.points.at(0).material.active_state.at(1)
        = std::numeric_limits<double>::max();
    unit.stiffness = 20.0;

    bool failure_propagated = false;
    try {
        static_cast<void>(prl::cell_engine::advance_owned_active_cell_overdamped_one_step(
            *current_cell,
            material,
            {unit},
            1.0e-3,
            10.0
        ));
    } catch(const std::runtime_error& error) {
        failure_propagated = std::string(error.what())
            == "active overdamped pre-step audit must be finite";
    }
    require(failure_propagated,
            "owned step did not propagate the post-assembly active-audit failure");

    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    require(after_mesh.vertices.size() == before_mesh.vertices.size(),
            "failed owned step changed the vertex count");
    for(std::size_t index = 0; index < before_mesh.vertices.size(); ++index) {
        require(after_mesh.vertices[index].persistent_id
                    == before_mesh.vertices[index].persistent_id
                && after_mesh.vertices[index].position
                    == before_mesh.vertices[index].position,
                "failed owned step committed a vertex position");
    }
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "failed owned step left a force buffer");
    }
    const auto expected_geometry = independent_geometry(after_mesh);
    require(nearly_equal(current_cell->get_area(), expected_geometry.area)
            && nearly_equal(current_cell->get_volume(), expected_geometry.volume),
            "failed owned step left stale area or volume caches");
    require(nearly_equal(current_cell->get_centroid().dx(), expected_geometry.centroid[0])
            && nearly_equal(current_cell->get_centroid().dy(), expected_geometry.centroid[1])
            && nearly_equal(current_cell->get_centroid().dz(), expected_geometry.centroid[2]),
            "failed owned step left a stale centroid cache");
    return 0;
}

int owned_step_uses_dual_area_damping() {
    using namespace prl::core;
    auto current_cell = passive_active_test_cell();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell),
    };
    const auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const prl::cell_engine::CellSurfaceDampingLaw damping{
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };

    const auto audit = prl::cell_engine::advance_owned_active_cell_overdamped_one_step(
        *current_cell,
        material,
        {unit},
        1.0e-3,
        damping
    );
    const auto before_geometry = independent_geometry(before_mesh);

    std::cout << std::setprecision(17)
              << "control_area_sum=" << audit.motion.control_area_sum
              << " min_nodal_damping=" << audit.motion.minimum_nodal_damping
              << " max_nodal_damping=" << audit.motion.maximum_nodal_damping
              << " total_force_l2=" << audit.motion.total_force_l2_norm
              << " displacement_l2=" << audit.motion.displacement_l2_norm
              << " force_work=" << audit.motion.total_force_work
              << " viscous_dissipation=" << audit.motion.viscous_dissipation
              << '\n';

    require(audit.motion.damping_measure
                == prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
            "owned driver did not preserve the dual-area damping measure");
    require(nearly_equal(audit.motion.control_area_sum, before_geometry.area),
            "owned driver dual areas do not partition the current surface");
    require(audit.motion.minimum_nodal_damping > 0.0
                && audit.motion.maximum_nodal_damping
                    >= audit.motion.minimum_nodal_damping,
            "owned driver reported invalid effective nodal damping");
    require(audit.motion.work_dissipation_residual <= tolerance,
            "owned dual-area force work and dissipation diverged");
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "owned dual-area step did not consume the force buffer");
    }
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        if(argc != 2) throw std::invalid_argument("one behavior name is required");
        const std::string behavior = argv[1];
        if(behavior == "passive_active_geometry_step") {
            return real_passive_active_step_refreshes_geometry();
        }
        if(behavior == "real_contact_step") {
            return real_contact_force_enters_the_owned_step();
        }
        if(behavior == "post_assembly_failure_cleanup") {
            return post_assembly_failure_cleans_force_buffers_without_motion();
        }
        if(behavior == "dual_area_owned_step") {
            return owned_step_uses_dual_area_damping();
        }
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "prl_cell_engine_owned_step_integration_test: "
                  << error.what() << '\n';
        return 1;
    }
}
