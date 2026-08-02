#include "prl/core/active_myocardial_mechanics.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

bool nearly_equal(const double left, const double right, const double allowed = tolerance) {
    return std::abs(left - right) <= allowed;
}

prl::core::SurfaceMeshSnapshot reference_mesh() {
    using namespace prl::core;
    return {
        17,
        7,
        {
            SurfaceVertex{10, {0.0, 0.0, 0.0}},
            SurfaceVertex{11, {1.0, 0.0, 0.0}},
            SurfaceVertex{12, {1.0, 1.0, 0.0}},
            SurfaceVertex{13, {0.0, 1.0, 0.0}},
        },
        {
            SurfaceFace{{0, 1, 2}},
            SurfaceFace{{0, 2, 3}},
        },
    };
}

prl::core::MyocardialCellMaterialState active_material_state() {
    using namespace prl::core;
    const auto activation = c1_activation_protocol(1.5, 0.0, 0.1);
    return {
        17,
        7,
        {
            {
                MyocardialMaterialState{
                    101,
                    SurfaceRegion::lateral,
                    {1.0, 0.0, 0.0},
                    {activation.activation, activation.activation_rate},
                },
                {10, 11, 12},
                {0.75, 0.25, 0.0},
                0.5,
            },
            {
                MyocardialMaterialState{
                    205,
                    SurfaceRegion::lateral,
                    {1.0, 0.0, 0.0},
                    {},
                },
                {10, 11, 12},
                {0.25, 0.75, 0.0},
                0.5,
            },
        },
    };
}

std::array<double, 3> force_for(
    const prl::core::ActiveContractionEvaluation& evaluation,
    const prl::core::VertexId vertex_id
) {
    for(const auto& vertex_force : evaluation.vertex_forces) {
        if(vertex_force.vertex_id == vertex_id) return vertex_force.force;
    }
    throw std::runtime_error("active force is missing a surface vertex");
}

prl::core::ActiveContractionUnit active_unit(
    const prl::core::SurfaceMeshSnapshot& mesh,
    const prl::core::MyocardialCellMaterialState& material
) {
    return prl::core::build_active_contraction_unit(
        mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.99
    );
}

int preferred_length_force_and_power_follow_the_frozen_contract() {
    using namespace prl::core;
    const auto mesh = reference_mesh();
    const auto material = active_material_state();
    const auto unit = active_unit(mesh, material);
    const auto evaluation = evaluate_active_contraction(mesh, material, {unit});
    const auto& state = evaluation.unit_states.at(0);

    const double pi = std::acos(-1.0);
    require(nearly_equal(unit.reference_length, 0.5), "reference length mismatch");
    require(nearly_equal(state.activation, 0.05), "activation mismatch");
    require(nearly_equal(state.activation_rate, 0.05 * pi), "activation rate mismatch");
    require(nearly_equal(state.length, 0.5), "current active length mismatch");
    require(nearly_equal(state.preferred_length, 0.475), "preferred length mismatch");
    require(nearly_equal(state.energy, 0.003125), "active energy mismatch");
    require(nearly_equal(state.input_power, 0.00625 * pi), "active input power mismatch");

    const auto force_10 = force_for(evaluation, 10);
    const auto force_11 = force_for(evaluation, 11);
    require(nearly_equal(force_10[0], 0.125), "minus-anchor scatter mismatch");
    require(nearly_equal(force_11[0], -0.125), "plus-anchor scatter mismatch");
    require(nearly_equal(force_10[1], 0.0) && nearly_equal(force_11[1], 0.0),
            "active force left the fiber axis");
    require(evaluation.audit.net_force_residual <= tolerance, "active net force is nonzero");
    require(evaluation.audit.net_moment_residual <= tolerance, "active net moment is nonzero");
    require(evaluation.audit.minimum_axis_fiber_alignment >= 1.0 - tolerance,
            "active axis is not fiber aligned");
    return 0;
}

int activation_protocol_matches_the_frozen_c1_envelope() {
    using namespace prl::core;
    const auto rest = c1_activation_protocol(0.5, 0.0, 0.1);
    const auto ramp_start = c1_activation_protocol(1.0, 0.0, 0.1);
    const auto ramp_midpoint = c1_activation_protocol(1.5, 0.0, 0.1);
    const auto hold_start = c1_activation_protocol(2.0, 0.0, 0.1);
    const auto release_start = c1_activation_protocol(3.0, 0.0, 0.1);
    const auto release_midpoint = c1_activation_protocol(3.5, 0.0, 0.1);
    const auto release_end = c1_activation_protocol(4.0, 0.0, 0.1);
    const double pi = std::acos(-1.0);

    require(nearly_equal(rest.activation, 0.0) && nearly_equal(rest.activation_rate, 0.0),
            "activation rest interval mismatch");
    require(nearly_equal(ramp_start.activation, 0.0)
            && nearly_equal(ramp_start.activation_rate, 0.0),
            "activation ramp does not start C1-smoothly");
    require(nearly_equal(ramp_midpoint.activation, 0.05)
            && nearly_equal(ramp_midpoint.activation_rate, 0.05 * pi),
            "activation cosine ramp mismatch");
    require(nearly_equal(hold_start.activation, 0.1)
            && nearly_equal(hold_start.activation_rate, 0.0),
            "activation hold does not start C1-smoothly");
    require(nearly_equal(release_start.activation, 0.1)
            && nearly_equal(release_start.activation_rate, 0.0),
            "activation release does not start C1-smoothly");
    require(nearly_equal(release_midpoint.activation, 0.05)
            && nearly_equal(release_midpoint.activation_rate, -0.05 * pi),
            "activation cosine release mismatch");
    require(nearly_equal(release_end.activation, 0.0)
            && nearly_equal(release_end.activation_rate, 0.0),
            "activation release does not end C1-smoothly");
    const auto delayed = c1_activation_protocol(2.5, 1.0, 0.1);
    require(nearly_equal(delayed.activation, ramp_midpoint.activation)
            && nearly_equal(delayed.activation_rate, ramp_midpoint.activation_rate),
            "activation delay mismatch");
    return 0;
}

int active_force_matches_the_energy_directional_derivative() {
    using namespace prl::core;
    const auto mesh = reference_mesh();
    const auto material = active_material_state();
    const auto unit = active_unit(mesh, material);
    std::array<std::array<double, 3>, 4> direction{{
        {0.2, -0.1, 0.0},
        {-0.3, 0.15, 0.0},
        {0.1, 0.25, 0.0},
        {-0.05, -0.2, 0.0},
    }};
    double direction_norm = 0.0;
    for(const auto& vector : direction) {
        for(const double value : vector) direction_norm += value * value;
    }
    direction_norm = std::sqrt(direction_norm);
    for(auto& vector : direction) {
        for(double& value : vector) value /= direction_norm;
    }

    const auto evaluation = evaluate_active_contraction(mesh, material, {unit});
    auto plus_mesh = mesh;
    auto minus_mesh = mesh;
    const double step = 1.0e-7;
    for(std::size_t vertex = 0; vertex < mesh.vertices.size(); ++vertex) {
        for(std::size_t component = 0; component < 3; ++component) {
            plus_mesh.vertices[vertex].position[component] += step * direction[vertex][component];
            minus_mesh.vertices[vertex].position[component] -= step * direction[vertex][component];
        }
    }
    const double plus_energy = evaluate_active_contraction(plus_mesh, material, {unit})
        .audit.total_energy;
    const double minus_energy = evaluate_active_contraction(minus_mesh, material, {unit})
        .audit.total_energy;
    const double finite_difference = (plus_energy - minus_energy) / (2.0 * step);
    double analytic = 0.0;
    for(std::size_t vertex = 0; vertex < mesh.vertices.size(); ++vertex) {
        const auto force = force_for(evaluation, mesh.vertices[vertex].persistent_id);
        for(std::size_t component = 0; component < 3; ++component) {
            analytic -= force[component] * direction[vertex][component];
        }
    }
    const double scale = std::max({1.0, std::abs(finite_difference), std::abs(analytic)});
    require(std::abs(finite_difference - analytic) / scale <= 1.0e-9,
            "active force does not match the energy directional derivative");
    require(evaluation.audit.net_force_residual <= tolerance, "active net force is nonzero");
    require(evaluation.audit.net_moment_residual <= tolerance, "active net moment is nonzero");
    return 0;
}

std::array<double, 3> rotate_z(const std::array<double, 3>& vector, const double angle) {
    return {
        std::cos(angle) * vector[0] - std::sin(angle) * vector[1],
        std::sin(angle) * vector[0] + std::cos(angle) * vector[1],
        vector[2],
    };
}

int active_mechanics_is_rigid_objective() {
    using namespace prl::core;
    const auto mesh = reference_mesh();
    const auto material = active_material_state();
    const auto unit = active_unit(mesh, material);
    const auto evaluation = evaluate_active_contraction(mesh, material, {unit});

    const double angle = 0.37;
    const std::array<double, 3> translation{0.7, -0.4, 0.2};
    auto transformed_mesh = mesh;
    for(auto& vertex : transformed_mesh.vertices) {
        vertex.position = rotate_z(vertex.position, angle);
        for(std::size_t component = 0; component < 3; ++component) {
            vertex.position[component] += translation[component];
        }
    }
    auto transformed_material = material;
    for(auto& point : transformed_material.points) {
        point.material.fiber_direction = rotate_z(point.material.fiber_direction, angle);
    }
    const auto transformed_unit = active_unit(transformed_mesh, transformed_material);
    const auto transformed = evaluate_active_contraction(
        transformed_mesh,
        transformed_material,
        {transformed_unit}
    );

    require(nearly_equal(transformed.audit.total_energy, evaluation.audit.total_energy, 1.0e-14),
            "active energy is not rigid objective");
    require(nearly_equal(
        transformed.audit.total_input_power,
        evaluation.audit.total_input_power,
        1.0e-14
    ), "active input power is not rigid objective");
    for(const auto& vertex : mesh.vertices) {
        const auto expected = rotate_z(force_for(evaluation, vertex.persistent_id), angle);
        const auto actual = force_for(transformed, vertex.persistent_id);
        for(std::size_t component = 0; component < 3; ++component) {
            require(nearly_equal(actual[component], expected[component], 1.0e-14),
                    "active nodal force is not rigid objective");
        }
    }
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        if(argc != 2) throw std::invalid_argument("one behavior name is required");
        const std::string behavior = argv[1];
        if(behavior == "preferred_length_force_power") {
            return preferred_length_force_and_power_follow_the_frozen_contract();
        }
        if(behavior == "activation_protocol") {
            return activation_protocol_matches_the_frozen_c1_envelope();
        }
        if(behavior == "directional_derivative") {
            return active_force_matches_the_energy_directional_derivative();
        }
        if(behavior == "rigid_objectivity") return active_mechanics_is_rigid_objective();
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "prl_active_myocardial_mechanics_test: " << error.what() << '\n';
        return 1;
    }
}
