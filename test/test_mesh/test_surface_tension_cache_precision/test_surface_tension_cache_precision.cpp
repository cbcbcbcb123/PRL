#include "cell.hpp"
#include "custom_structures.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

using Vector3 = std::array<double, 3>;

Vector3 add(const Vector3& first, const Vector3& second) {
    return {
        first[0] + second[0],
        first[1] + second[1],
        first[2] + second[2],
    };
}

Vector3 subtract(const Vector3& first, const Vector3& second) {
    return {
        first[0] - second[0],
        first[1] - second[1],
        first[2] - second[2],
    };
}

Vector3 scale(const Vector3& value, const double factor) {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

double dot(const Vector3& first, const Vector3& second) {
    return first[0] * second[0]
        + first[1] * second[1]
        + first[2] * second[2];
}

Vector3 cross(const Vector3& first, const Vector3& second) {
    return {
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    };
}

double norm(const Vector3& value) {
    return std::sqrt(dot(value, value));
}

Vector3 position(const mesh& surface_mesh, const unsigned index) {
    return {
        surface_mesh.node_pos_lst.at(3 * index),
        surface_mesh.node_pos_lst.at(3 * index + 1),
        surface_mesh.node_pos_lst.at(3 * index + 2),
    };
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

void project_vertices_to_unit_sphere(mesh& surface_mesh) {
    for(std::size_t offset = 0; offset < surface_mesh.node_pos_lst.size(); offset += 3) {
        const Vector3 value{
            surface_mesh.node_pos_lst[offset],
            surface_mesh.node_pos_lst[offset + 1],
            surface_mesh.node_pos_lst[offset + 2],
        };
        const double radius = norm(value);
        if(!std::isfinite(radius) || radius <= 0.0) {
            throw std::runtime_error("invalid projected icosphere vertex");
        }
        for(std::size_t component = 0; component < 3; ++component) {
            surface_mesh.node_pos_lst[offset + component] /= radius;
        }
    }
}

mesh icosphere_mesh(const std::size_t level) {
    const double phi = 0.5 * (1.0 + std::sqrt(5.0));
    mesh result;
    result.node_pos_lst = {
        -1.0,  phi,  0.0,   1.0,  phi,  0.0,
        -1.0, -phi,  0.0,   1.0, -phi,  0.0,
         0.0, -1.0,  phi,   0.0,  1.0,  phi,
         0.0, -1.0, -phi,   0.0,  1.0, -phi,
         phi,  0.0, -1.0,   phi,  0.0,  1.0,
        -phi,  0.0, -1.0,  -phi,  0.0,  1.0,
    };
    result.face_point_ids = {
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1},
    };
    project_vertices_to_unit_sphere(result);
    for(std::size_t refinement = 0; refinement < level; ++refinement) {
        result = midpoint_refined(result);
        project_vertices_to_unit_sphere(result);
    }
    return result;
}

std::shared_ptr<cell_type_parameters> surface_tension_cell_type(
    const double surface_tension
) {
    face_type_parameters face_type;
    face_type.name_ = "v04_surface_tension";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = surface_tension;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 0.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "v04_cache_precision";
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

double surface_area_with_displacement(
    const mesh& surface_mesh,
    const std::vector<Vector3>& direction,
    const double factor
) {
    double area = 0.0;
    for(const auto& triangle : surface_mesh.face_point_ids) {
        const auto a = add(position(surface_mesh, triangle[0]),
                           scale(direction.at(triangle[0]), factor));
        const auto b = add(position(surface_mesh, triangle[1]),
                           scale(direction.at(triangle[1]), factor));
        const auto c = add(position(surface_mesh, triangle[2]),
                           scale(direction.at(triangle[2]), factor));
        area += 0.5 * norm(cross(subtract(b, a), subtract(c, a)));
    }
    return area;
}

struct PrecisionAudit {
    bool getter_is_double{};
    std::size_t vertex_count{};
    std::size_t face_count{};
    double registered_energy{};
    double legacy_energy{};
    double legacy_ratio{};
    double legacy_ratio_error{};
    double directional_residual{};
    double normal_relative_l2{};
    double tangential_relative_l2{};
    double normalized_net_force{};
    double normalized_force_formula_residual{};
    bool force_buffers_cleared{};
};

} // namespace

class cell_tester {
public:
    PrecisionAudit audit_level_five_cache_precision() {
        constexpr double surface_tension = 0.02;
        constexpr double damping_per_area = 10.0;
        auto surface_mesh = icosphere_mesh(5);
        auto current_cell = std::make_shared<cell>(
            surface_mesh,
            901,
            surface_tension_cell_type(surface_tension)
        );
        current_cell->initialize_cell_properties();

        const std::size_t vertex_count = surface_mesh.node_pos_lst.size() / 3;
        std::vector<Vector3> expected_forces(vertex_count, Vector3{});
        std::vector<double> control_areas(vertex_count, 0.0);
        double area = 0.0;
        std::unordered_set<std::uint64_t> edges;
        double squared_edge_sum = 0.0;
        for(const auto& triangle : surface_mesh.face_point_ids) {
            const auto a = position(surface_mesh, triangle[0]);
            const auto b = position(surface_mesh, triangle[1]);
            const auto c = position(surface_mesh, triangle[2]);
            const auto oriented = cross(subtract(b, a), subtract(c, a));
            const double double_area = norm(oriented);
            const double face_area = 0.5 * double_area;
            const auto normal = scale(oriented, 1.0 / double_area);
            area += face_area;
            for(const auto index : triangle) control_areas[index] += face_area / 3.0;
            const std::array<Vector3, 3> gradients{
                scale(cross(normal, subtract(b, c)), -0.5),
                scale(cross(normal, subtract(c, a)), -0.5),
                scale(cross(normal, subtract(a, b)), -0.5),
            };
            for(std::size_t local = 0; local < 3; ++local) {
                expected_forces[triangle[local]] = add(
                    expected_forces[triangle[local]],
                    scale(gradients[local], -surface_tension)
                );
                const auto first = triangle[local];
                const auto second = triangle[(local + 1) % 3];
                const auto key = edge_key(first, second);
                if(edges.insert(key).second) {
                    const auto delta = subtract(
                        position(surface_mesh, first),
                        position(surface_mesh, second)
                    );
                    squared_edge_sum += dot(delta, delta);
                }
            }
        }

        std::vector<Vector3> direction;
        direction.reserve(vertex_count);
        double maximum_direction_norm = 0.0;
        for(std::size_t index = 0; index < vertex_count; ++index) {
            const auto point = position(surface_mesh, static_cast<unsigned>(index));
            const auto normal = scale(point, 1.0 / norm(point));
            const double amplitude = 0.25
                + 0.10 * point[0] + 0.07 * point[1] - 0.05 * point[2];
            const Vector3 tangent{
                -normal[2] * normal[0],
                -normal[2] * normal[1],
                1.0 - normal[2] * normal[2],
            };
            direction.push_back(add(scale(normal, amplitude), scale(tangent, 0.05)));
            maximum_direction_norm = std::max(
                maximum_direction_norm,
                norm(direction.back())
            );
        }
        for(auto& value : direction) value = scale(value, 1.0 / maximum_direction_norm);
        const double h_rms = std::sqrt(
            squared_edge_sum / static_cast<double>(edges.size())
        );
        const double epsilon = 1.0e-6 * h_rms;
        const double finite_difference = surface_tension * (
            surface_area_with_displacement(surface_mesh, direction, epsilon)
            - surface_area_with_displacement(surface_mesh, direction, -epsilon)
        ) / (2.0 * epsilon);

        current_cell->apply_internal_forces(0.0);
        const double registered_energy = surface_tension * area;
        const double legacy_energy = current_cell->get_surface_tension_energy();
        double force_directional = 0.0;
        double force_difference_square = 0.0;
        double expected_force_square = 0.0;
        double normal_error_square_integral = 0.0;
        double tangential_square_integral = 0.0;
        double control_area_sum = 0.0;
        Vector3 net_force{};
        const double exact_normal_velocity = -2.0 * surface_tension / damping_per_area;
        for(std::size_t index = 0; index < vertex_count; ++index) {
            const auto& node_force = current_cell->node_lst_.at(index).force();
            const Vector3 actual_force{
                node_force.dx(), node_force.dy(), node_force.dz()
            };
            const auto force_delta = subtract(actual_force, expected_forces[index]);
            force_difference_square += dot(force_delta, force_delta);
            expected_force_square += dot(expected_forces[index], expected_forces[index]);
            force_directional -= dot(actual_force, direction[index]);
            net_force = add(net_force, actual_force);

            const auto point = position(surface_mesh, static_cast<unsigned>(index));
            const auto normal = scale(point, 1.0 / norm(point));
            const auto velocity = scale(
                actual_force,
                1.0 / (damping_per_area * control_areas[index])
            );
            const double normal_velocity = dot(velocity, normal);
            const auto tangential = subtract(
                velocity,
                scale(normal, normal_velocity)
            );
            const double normal_error = normal_velocity - exact_normal_velocity;
            normal_error_square_integral += control_areas[index]
                * normal_error * normal_error;
            tangential_square_integral += control_areas[index]
                * dot(tangential, tangential);
            control_area_sum += control_areas[index];
        }
        const double directional_denominator = std::max({
            std::abs(finite_difference),
            std::abs(force_directional),
            registered_energy,
            1.0e-30,
        });

        for(auto& current_node : current_cell->node_lst_) {
            current_node.force_.reset();
        }
        const bool force_buffers_cleared = std::all_of(
            current_cell->node_lst_.begin(),
            current_cell->node_lst_.end(),
            [](const node& current_node) {
                return current_node.force().dx() == 0.0
                    && current_node.force().dy() == 0.0
                    && current_node.force().dz() == 0.0;
            }
        );

        PrecisionAudit result;
        result.getter_is_double = std::is_same_v<
            decltype(std::declval<const cell&>().get_surface_tension_energy()),
            double
        >;
        result.vertex_count = vertex_count;
        result.face_count = surface_mesh.face_point_ids.size();
        result.registered_energy = registered_energy;
        result.legacy_energy = legacy_energy;
        result.legacy_ratio = legacy_energy / registered_energy;
        result.legacy_ratio_error = std::abs(result.legacy_ratio - 0.5);
        result.directional_residual = std::abs(
            finite_difference - force_directional
        ) / directional_denominator;
        result.normal_relative_l2 = std::sqrt(
            normal_error_square_integral / control_area_sum
        ) / std::abs(exact_normal_velocity);
        result.tangential_relative_l2 = std::sqrt(
            tangential_square_integral / control_area_sum
        ) / std::abs(exact_normal_velocity);
        result.normalized_net_force = norm(net_force)
            / (surface_tension * area);
        result.normalized_force_formula_residual = std::sqrt(force_difference_square)
            / std::max(1.0, std::sqrt(expected_force_square));
        result.force_buffers_cleared = force_buffers_cleared;
        return result;
    }
};

int main() {
    try {
        const auto audit = cell_tester{}.audit_level_five_cache_precision();
        std::cerr << std::setprecision(17)
                  << "v04_cache_precision"
                  << ",getter_is_double," << audit.getter_is_double
                  << ",vertices," << audit.vertex_count
                  << ",faces," << audit.face_count
                  << ",registered_energy," << audit.registered_energy
                  << ",legacy_energy," << audit.legacy_energy
                  << ",legacy_ratio," << audit.legacy_ratio
                  << ",legacy_ratio_error," << audit.legacy_ratio_error
                  << ",directional_residual," << audit.directional_residual
                  << ",normal_l2," << audit.normal_relative_l2
                  << ",tangent_l2," << audit.tangential_relative_l2
                  << ",net_force," << audit.normalized_net_force
                  << ",force_formula_residual,"
                  << audit.normalized_force_formula_residual
                  << ",force_buffers_cleared," << audit.force_buffers_cleared
                  << '\n';
        const auto matches_frozen = [](const double current, const double frozen) {
            return std::abs(current - frozen)
                / std::max(1.0, std::abs(frozen)) <= 1.0e-12;
        };
        if(audit.vertex_count != 10242 || audit.face_count != 20480
           || !matches_frozen(audit.registered_energy, 0.25125226936116585)
           || !matches_frozen(
                audit.directional_residual,
                6.8942747977147815e-08
              )
           || !matches_frozen(audit.normal_relative_l2, 0.0044003196067863275)
           || !matches_frozen(
                audit.tangential_relative_l2,
                0.00068763631315451972
              )
           || !matches_frozen(
                audit.normalized_net_force,
                1.8168641637451863e-15
              )
           || audit.normalized_force_formula_residual > 1.0e-12
           || !audit.force_buffers_cleared) {
            throw std::runtime_error("surface-tension mechanics changed from RED baseline");
        }
        if(!audit.getter_is_double) {
            throw std::runtime_error("surface-tension cache getter is not double");
        }
        if(audit.legacy_ratio_error > 1.0e-10) {
            throw std::runtime_error("level-5 surface-tension cache lost precision");
        }
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "test_surface_tension_cache_precision: "
                  << error.what() << '\n';
        return 1;
    }
}
