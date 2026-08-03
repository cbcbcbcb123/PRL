#include "prl/cell_engine/short_trajectory.hpp"
#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "custom_structures.hpp"
#include "node.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

cell_ptr active_test_cell() {
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
    return std::make_shared<cell>(cell_mesh, 17);
}

prl::core::VertexId persistent_node_id(
    const cell& current_cell,
    const unsigned local_id
) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

prl::core::MyocardialCellMaterialState active_material(const cell& current_cell) {
    using namespace prl::core;
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        17,
        0,
        {
            {
                MyocardialMaterialState{
                    101,
                    SurfaceRegion::apical,
                    {1.0, 0.0, 0.0},
                    {0.05, 0.0},
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
        },
    };
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

std::uint64_t edge_key(unsigned first, unsigned second) {
    if(first > second) std::swap(first, second);
    return (static_cast<std::uint64_t>(first) << 32U)
        | static_cast<std::uint64_t>(second);
}

mesh midpoint_refined(const mesh& input) {
    mesh result;
    result.node_pos_lst = input.node_pos_lst;
    result.face_point_ids.reserve(input.face_point_ids.size() * 4);
    std::unordered_map<std::uint64_t, unsigned> midpoint_by_edge;
    auto midpoint = [&](const unsigned first, const unsigned second) {
        const auto key = edge_key(first, second);
        const auto found = midpoint_by_edge.find(key);
        if(found != midpoint_by_edge.end()) return found->second;
        const auto id = static_cast<unsigned>(result.node_pos_lst.size() / 3);
        for(std::size_t component = 0; component < 3; ++component) {
            result.node_pos_lst.push_back(0.5 * (
                input.node_pos_lst.at(3 * first + component)
                + input.node_pos_lst.at(3 * second + component)
            ));
        }
        midpoint_by_edge.emplace(key, id);
        return id;
    };
    for(const auto& triangle : input.face_point_ids) {
        const auto ab = midpoint(triangle[0], triangle[1]);
        const auto bc = midpoint(triangle[1], triangle[2]);
        const auto ca = midpoint(triangle[2], triangle[0]);
        result.face_point_ids.push_back({triangle[0], ab, ca});
        result.face_point_ids.push_back({ab, triangle[1], bc});
        result.face_point_ids.push_back({ca, bc, triangle[2]});
        result.face_point_ids.push_back({ab, bc, ca});
    }
    return result;
}

std::shared_ptr<cell_type_parameters> surface_tension_cell_type() {
    face_type_parameters face_type;
    face_type.name_ = "registered_surface_tension";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = 0.02;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 0.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "x1k_surface_tension";
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

cell_ptr surface_tension_cell(const mesh& surface_mesh, const unsigned cell_id) {
    auto result = std::make_shared<cell>(
        surface_mesh,
        cell_id,
        surface_tension_cell_type()
    );
    result->initialize_cell_properties();
    return result;
}

int active_fixed_topology_trajectory_records_stepwise_qois() {
    auto current_cell = active_test_cell();
    const auto material = active_material(*current_cell);
    const auto initial_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto unit = prl::core::build_active_contraction_unit(
        initial_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    prl::cell_engine::ActiveShortTrajectoryConfig config;
    config.time_step = 2.5e-3;
    config.step_count = 8;
    config.qoi_contraction_unit_id = 501;
    config.damping = {
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };

    const auto audit = prl::cell_engine::run_active_fixed_topology_short_trajectory(
        *current_cell,
        material,
        {unit},
        config
    );
    require(audit.status == prl::cell_engine::ShortTrajectoryStatus::passed,
            "frozen coarse active trajectory did not complete");
    require(!audit.failure.has_value(),
            "passed active trajectory retained a failure record");
    require(audit.samples.size() == 9
                && audit.samples.front().step == 0
                && audit.samples.back().step == 8
                && std::abs(audit.samples.back().time - 0.02) <= 1.0e-15,
            "active trajectory sampling contract is wrong");
    require(audit.samples.front().registered_active_energy > 1.0e-2
                && audit.samples.back().registered_active_energy
                    < audit.samples.front().registered_active_energy,
            "active trajectory did not start nontrivially and descend");

    for(const auto& sample : audit.samples) {
        require(std::isfinite(sample.axis_length)
                    && std::isfinite(sample.contraction)
                    && std::isfinite(sample.area_ratio)
                    && std::isfinite(sample.volume_ratio)
                    && std::isfinite(sample.registered_active_energy)
                    && std::isfinite(sample.energy_balance_residual),
                "active trajectory emitted a non-finite QoI");
        require(sample.minimum_oriented_face_alignment > 0.0
                    && sample.minimum_triangle_quality >= 0.05
                    && sample.minimum_face_area_ratio >= 1.0e-4,
                "active trajectory violated a frozen surface-quality gate");
        require(sample.maximum_normalized_cache_residual <= 1.0e-12,
                "active trajectory cache disagrees with independent geometry");
    }
    require(audit.samples.back().normalized_surface_centroid_drift <= 1.0e-2,
            "active trajectory surface centroid drift exceeded its frozen gate");
    require(audit.samples.back().volume_ratio >= 0.5
                && audit.samples.back().volume_ratio <= 1.5,
            "active trajectory volume-ratio sanity gate failed");

    std::cout << std::setprecision(17)
              << "dt=" << config.time_step
              << " steps=" << config.step_count
              << " final_axis=" << audit.samples.back().axis_length
              << " final_contraction=" << audit.samples.back().contraction
              << " final_area_ratio=" << audit.samples.back().area_ratio
              << " final_volume_ratio=" << audit.samples.back().volume_ratio
              << " final_active_energy="
              << audit.samples.back().registered_active_energy
              << " cumulative_positive_energy_residual="
              << audit.cumulative_positive_energy_balance_residual
              << " min_quality=" << audit.minimum_triangle_quality
              << " min_orientation=" << audit.minimum_oriented_face_alignment
              << " max_cache_residual=" << audit.maximum_normalized_cache_residual
              << '\n';
    return 0;
}

prl::cell_engine::ActiveShortTrajectoryAudit run_active_level(
    const double time_step,
    const std::size_t step_count
) {
    auto current_cell = active_test_cell();
    const auto material = active_material(*current_cell);
    const auto initial_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto unit = prl::core::build_active_contraction_unit(
        initial_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    prl::cell_engine::ActiveShortTrajectoryConfig config;
    config.time_step = time_step;
    config.step_count = step_count;
    config.qoi_contraction_unit_id = 501;
    config.damping = {
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };
    return prl::cell_engine::run_active_fixed_topology_short_trajectory(
        *current_cell,
        material,
        {unit},
        config
    );
}

int active_time_refinement_passes_the_frozen_gate() {
    const auto coarse = run_active_level(2.5e-3, 8);
    const auto medium = run_active_level(1.25e-3, 16);
    const auto fine = run_active_level(6.25e-4, 32);
    require(coarse.status == prl::cell_engine::ShortTrajectoryStatus::passed
                && medium.status == prl::cell_engine::ShortTrajectoryStatus::passed
                && fine.status == prl::cell_engine::ShortTrajectoryStatus::passed,
            "one frozen time-refinement level failed before comparison");

    const prl::cell_engine::ActiveTimeRefinementThresholds thresholds{
        2.0e-3,
        0.5,
        1.0e-12,
        5.0e-3,
        1.5,
    };
    const auto gate = prl::cell_engine::evaluate_active_time_refinement(
        coarse,
        medium,
        fine,
        thresholds
    );
    require(gate.state.passed
                && gate.axis_length.passed
                && gate.contraction.passed
                && gate.area_ratio.passed
                && gate.volume_ratio.passed
                && gate.registered_active_energy.passed,
            "one objective time-refinement QoI failed self-convergence");
    require(gate.energy_residual_passed,
            "time-refined registered-energy residual did not shrink");
    require(gate.passed,
            "frozen active time-refinement gate failed");

    std::cout << std::setprecision(17)
              << "state_e_cm=" << gate.state.coarse_medium_normalized_error
              << " state_e_mf=" << gate.state.medium_fine_normalized_error
              << " state_p=" << gate.state.observed_order
              << " axis_p=" << gate.axis_length.observed_order
              << " contraction_p=" << gate.contraction.observed_order
              << " area_p=" << gate.area_ratio.observed_order
              << " volume_p=" << gate.volume_ratio.observed_order
              << " energy_p=" << gate.registered_active_energy.observed_order
              << " energy_residuals="
              << gate.coarse_normalized_positive_energy_residual << ','
              << gate.medium_normalized_positive_energy_residual << ','
              << gate.fine_normalized_positive_energy_residual
              << '\n';
    return 0;
}

int surface_tension_trajectory_records_registered_energy() {
    auto current_cell = surface_tension_cell(cube_surface_mesh(), 41);
    prl::cell_engine::SurfaceTensionShortTrajectoryConfig config;
    config.time_step = 1.0e-4;
    config.step_count = 20;
    config.surface_tension = 0.02;
    config.damping = {
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };
    const auto audit
        = prl::cell_engine::run_surface_tension_fixed_topology_short_trajectory(
            *current_cell,
            config
        );
    require(audit.status == prl::cell_engine::ShortTrajectoryStatus::passed
                && audit.samples.size() == 21,
            "surface-tension trajectory did not complete its frozen steps");
    require(audit.samples.front().registered_surface_energy > 0.0
                && audit.samples.back().registered_surface_energy
                    < audit.samples.front().registered_surface_energy,
            "registered surface-tension energy did not descend");
    require(audit.normalized_positive_energy_balance_residual <= 1.0e-3,
            "surface-tension coverage energy gate failed");
    require(audit.minimum_oriented_face_alignment > 0.0
                && audit.minimum_triangle_quality >= 0.05
                && audit.minimum_face_area_ratio >= 1.0e-4
                && audit.maximum_normalized_cache_residual <= 1.0e-12,
            "surface-tension trajectory failed a geometry gate");
    std::cout << std::setprecision(17)
              << "surface_vertices=" << current_cell->get_nb_of_nodes()
              << " surface_faces=" << current_cell->get_nb_of_faces()
              << " final_area_ratio=" << audit.samples.back().area_ratio
              << " final_volume_ratio=" << audit.samples.back().volume_ratio
              << " final_energy_ratio=" << audit.samples.back().energy_ratio
              << " normalized_centroid_drift="
              << audit.samples.back().normalized_surface_centroid_drift
              << " normalized_positive_energy_residual="
              << audit.normalized_positive_energy_balance_residual
              << '\n';
    return 0;
}

prl::cell_engine::SurfaceTensionShortTrajectoryAudit run_surface_level(
    const mesh& surface_mesh,
    const unsigned cell_id
) {
    auto current_cell = surface_tension_cell(surface_mesh, cell_id);
    prl::cell_engine::SurfaceTensionShortTrajectoryConfig config;
    config.time_step = 1.0e-4;
    config.step_count = 20;
    config.surface_tension = 0.02;
    config.damping = {
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };
    return prl::cell_engine::run_surface_tension_fixed_topology_short_trajectory(
        *current_cell,
        config
    );
}

int surface_tension_spatial_refinement_passes_objective_qois() {
    const auto coarse_mesh = cube_surface_mesh();
    const auto base_mesh = midpoint_refined(coarse_mesh);
    const auto fine_mesh = midpoint_refined(base_mesh);
    require(coarse_mesh.node_pos_lst.size() / 3 == 8
                && coarse_mesh.face_point_ids.size() == 12
                && base_mesh.node_pos_lst.size() / 3 == 26
                && base_mesh.face_point_ids.size() == 48
                && fine_mesh.node_pos_lst.size() / 3 == 98
                && fine_mesh.face_point_ids.size() == 192,
            "frozen spatial-refinement mesh matrix changed");
    const auto coarse = run_surface_level(coarse_mesh, 41);
    const auto base = run_surface_level(base_mesh, 42);
    const auto fine = run_surface_level(fine_mesh, 43);
    require(coarse.status == prl::cell_engine::ShortTrajectoryStatus::passed
                && base.status == prl::cell_engine::ShortTrajectoryStatus::passed
                && fine.status == prl::cell_engine::ShortTrajectoryStatus::passed,
            "one frozen spatial-refinement level failed before comparison");

    const prl::cell_engine::SurfaceTensionSpatialRefinementThresholds thresholds{
        2.0e-2,
        0.25,
        1.0e-10,
        1.0e-3,
        0.05,
        1.0e-12,
    };
    const auto gate = prl::cell_engine::evaluate_surface_tension_spatial_refinement(
        coarse,
        base,
        fine,
        thresholds
    );
    auto print_series = [](const char* const level,
                           const auto& trajectory) {
        for(const auto& sample : trajectory.samples) {
            std::cerr << std::setprecision(17)
                      << "series," << level
                      << ',' << sample.step
                      << ',' << sample.time
                      << ',' << sample.area_ratio
                      << ',' << sample.volume_ratio
                      << ',' << sample.energy_ratio
                      << ',' << sample.normalized_surface_centroid_drift
                      << ',' << sample.energy_balance_residual
                      << ',' << sample.minimum_oriented_face_alignment
                      << ',' << sample.minimum_triangle_quality
                      << ',' << sample.minimum_face_area_ratio
                      << ',' << sample.maximum_normalized_cache_residual
                      << '\n';
        }
    };
    print_series("coarse", coarse);
    print_series("base", base);
    print_series("fine", fine);
    std::cerr << std::setprecision(17)
              << "gate,area_errors,"
              << gate.area_ratio.coarse_medium_normalized_error << ','
              << gate.area_ratio.medium_fine_normalized_error
              << ",area_p," << gate.area_ratio.observed_order
              << ",volume_errors,"
              << gate.volume_ratio.coarse_medium_normalized_error << ','
              << gate.volume_ratio.medium_fine_normalized_error
              << ",volume_p," << gate.volume_ratio.observed_order
              << ",energy_p," << gate.registered_energy_ratio.observed_order
              << ",centroid_errors,"
              << gate.normalized_surface_centroid_drift
                    .coarse_medium_normalized_error
              << ','
              << gate.normalized_surface_centroid_drift
                    .medium_fine_normalized_error
              << ",centroid_p,"
              << gate.normalized_surface_centroid_drift.observed_order
              << ",min_quality," << gate.minimum_triangle_quality
              << ",max_cache," << gate.maximum_normalized_cache_residual
              << ",coverage_energy_residuals,"
              << coarse.normalized_positive_energy_balance_residual << ','
              << base.normalized_positive_energy_balance_residual << ','
              << fine.normalized_positive_energy_balance_residual
              << ",qoi_passes,"
              << gate.area_ratio.passed << ','
              << gate.volume_ratio.passed << ','
              << gate.registered_energy_ratio.passed << ','
              << gate.normalized_surface_centroid_drift.passed
              << ",other_passes,"
              << gate.energy_coverage_passed << ','
              << gate.surface_quality_passed << ','
              << gate.cache_consistency_passed
              << '\n';
    require(gate.area_ratio.passed
                && gate.volume_ratio.passed
                && gate.registered_energy_ratio.passed
                && gate.normalized_surface_centroid_drift.passed,
            "one objective spatial QoI failed self-convergence");
    require(gate.energy_coverage_passed
                && gate.surface_quality_passed
                && gate.cache_consistency_passed
                && gate.passed,
            "frozen surface-tension spatial gate failed");
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        if(argc != 2) throw std::invalid_argument("one behavior name is required");
        const std::string behavior = argv[1];
        if(behavior == "active_fixed_topology") {
            return active_fixed_topology_trajectory_records_stepwise_qois();
        }
        if(behavior == "active_time_refinement") {
            return active_time_refinement_passes_the_frozen_gate();
        }
        if(behavior == "surface_tension_trajectory") {
            return surface_tension_trajectory_records_registered_energy();
        }
        if(behavior == "surface_tension_spatial_refinement") {
            return surface_tension_spatial_refinement_passes_objective_qois();
        }
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "prl_short_trajectory_integration_test: "
                  << error.what() << '\n';
        return 1;
    }
}
