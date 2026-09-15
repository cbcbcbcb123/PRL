#include "cell.hpp"
#include "custom_structures.hpp"
#include "local_mesh_refiner.hpp"
#include "prl_cell_engine/cell_surface_force.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <omp.h>

namespace {

using Vector3 = std::array<double, 3>;
using Matrix3 = std::array<std::array<double, 3>, 3>;
using prl::cell_engine::SurfaceDampingLaw;
using prl::cell_engine::SurfaceDampingMeasure;
using prl::cell_engine::SurfaceVertexForce;

constexpr double kPi = 3.1415926535897932384626433832795;
constexpr double kTargetVolume = 167.875410364543;
constexpr double kEquivalentRadius = 3.42215355382543;
constexpr double kSurfaceTension = 0.160;
constexpr double kBendingModulus = 0.0100;
constexpr double kAreaElasticityModulus = 0.050;
constexpr double kBulkModulus = 30.0;
constexpr double kSurfaceDampingDensity = 1.0;
constexpr double kRampCoordinate = 10.0;
constexpr double kHoldCoordinate = 400.0;
constexpr double kPerturbationAmplitude = 0.02;
constexpr double kRotationDegrees = 37.0;
constexpr double kTiny = 1.0e-30;

struct RunConfig {
    std::string condition;
    unsigned face_count{};
    unsigned subdivision_level{};
    double time_step{};
    double stress_amplitude{};
    bool cytoskeleton_enabled{true};
    bool perturbed{false};
    double rotation_radians{};
};

struct MeshMeasure {
    double area{};
    double signed_volume{};
};

struct CytoskeletonLoad {
    std::vector<Vector3> nodal_forces;
    Matrix3 stress{};
    Vector3 long_axis{};
    Vector3 transverse_axis{};
    Vector3 thickness_axis{};
    double absolute_force_residual{};
    double relative_force_residual{};
    double absolute_moment_residual{};
    double relative_moment_residual{};
};

Vector3 add(const Vector3& a, const Vector3& b) {
    return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
}

Vector3 subtract(const Vector3& a, const Vector3& b) {
    return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}

Vector3 scale(const Vector3& a, const double factor) {
    return {factor * a[0], factor * a[1], factor * a[2]};
}

double dot(const Vector3& a, const Vector3& b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

Vector3 cross(const Vector3& a, const Vector3& b) {
    return {
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    };
}

double norm(const Vector3& value) {
    return std::sqrt(dot(value, value));
}

Vector3 normalized(const Vector3& value) {
    const double magnitude = norm(value);
    if(!(magnitude > 0.0) || !std::isfinite(magnitude)) {
        throw std::runtime_error("cannot normalize zero or non-finite vector");
    }
    return scale(value, 1.0 / magnitude);
}

Vector3 from_vec3(const vec3& value) {
    return {value.dx(), value.dy(), value.dz()};
}

Vector3 node_position(const node& current_node) {
    return from_vec3(current_node.pos());
}

Vector3 node_force(const node& current_node) {
    return from_vec3(current_node.force());
}

bool finite(const Vector3& value) {
    return std::isfinite(value[0]) && std::isfinite(value[1]) && std::isfinite(value[2]);
}

Vector3 rotate_z(const Vector3& value, const double angle) {
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    return {
        cosine * value[0] - sine * value[1],
        sine * value[0] + cosine * value[1],
        value[2],
    };
}

Matrix3 dyadic(const Vector3& axis, const double coefficient) {
    Matrix3 result{};
    for(std::size_t row = 0; row < 3; ++row) {
        for(std::size_t column = 0; column < 3; ++column) {
            result[row][column] = coefficient * axis[row] * axis[column];
        }
    }
    return result;
}

Matrix3 matrix_add(const Matrix3& first, const Matrix3& second) {
    Matrix3 result{};
    for(std::size_t row = 0; row < 3; ++row) {
        for(std::size_t column = 0; column < 3; ++column) {
            result[row][column] = first[row][column] + second[row][column];
        }
    }
    return result;
}

Vector3 matrix_vector(const Matrix3& matrix, const Vector3& vector) {
    Vector3 result{};
    for(std::size_t row = 0; row < 3; ++row) {
        for(std::size_t column = 0; column < 3; ++column) {
            result[row] += matrix[row][column] * vector[column];
        }
    }
    return result;
}

Vector3 solve_linear_system(Matrix3 matrix, Vector3 right_hand_side) {
    for(std::size_t pivot = 0; pivot < 3; ++pivot) {
        std::size_t best = pivot;
        for(std::size_t row = pivot + 1; row < 3; ++row) {
            if(std::abs(matrix[row][pivot]) > std::abs(matrix[best][pivot])) best = row;
        }
        if(std::abs(matrix[best][pivot]) < 1.0e-20) {
            throw std::runtime_error("singular rigid-mode correction matrix");
        }
        std::swap(matrix[pivot], matrix[best]);
        std::swap(right_hand_side[pivot], right_hand_side[best]);
        const double diagonal = matrix[pivot][pivot];
        for(std::size_t column = pivot; column < 3; ++column) matrix[pivot][column] /= diagonal;
        right_hand_side[pivot] /= diagonal;
        for(std::size_t row = 0; row < 3; ++row) {
            if(row == pivot) continue;
            const double factor = matrix[row][pivot];
            for(std::size_t column = pivot; column < 3; ++column) {
                matrix[row][column] -= factor * matrix[pivot][column];
            }
            right_hand_side[row] -= factor * right_hand_side[pivot];
        }
    }
    return right_hand_side;
}

unsigned subdivision_from_face_count(const unsigned face_count) {
    if(face_count == 80) return 1;
    if(face_count == 320) return 2;
    if(face_count == 1280) return 3;
    throw std::invalid_argument("face count must be one of 80, 320, 1280");
}

RunConfig parse_config(
    const std::string& condition,
    const unsigned face_count,
    const double time_step,
    const double stress_amplitude
) {
    const std::set<std::string> allowed{"PILOT", "FULL", "ABLATION", "PERTURBED", "ROTATED37"};
    if(allowed.count(condition) == 0) throw std::invalid_argument("unknown condition: " + condition);
    if(!(time_step > 0.0) || !std::isfinite(time_step)) {
        throw std::invalid_argument("time step must be finite and positive");
    }
    if(!(stress_amplitude >= 0.0) || !std::isfinite(stress_amplitude)) {
        throw std::invalid_argument("stress amplitude must be finite and non-negative");
    }
    RunConfig config;
    config.condition = condition;
    config.face_count = face_count;
    config.subdivision_level = subdivision_from_face_count(face_count);
    config.time_step = time_step;
    config.stress_amplitude = stress_amplitude;
    config.cytoskeleton_enabled = condition != "ABLATION";
    config.perturbed = condition == "ABLATION" || condition == "PERTURBED";
    config.rotation_radians = condition == "ROTATED37" ? kRotationDegrees * kPi / 180.0 : 0.0;
    return config;
}

MeshMeasure measure_mesh(const mesh& geometry) {
    auto point = [&](const unsigned id) {
        return Vector3{
            geometry.node_pos_lst.at(3 * id),
            geometry.node_pos_lst.at(3 * id + 1),
            geometry.node_pos_lst.at(3 * id + 2),
        };
    };
    MeshMeasure measure;
    for(const auto& triangle : geometry.face_point_ids) {
        const Vector3 a = point(triangle[0]);
        const Vector3 b = point(triangle[1]);
        const Vector3 c = point(triangle[2]);
        measure.area += 0.5 * norm(cross(subtract(b, a), subtract(c, a)));
        measure.signed_volume += dot(a, cross(b, c)) / 6.0;
    }
    return measure;
}

mesh make_icosphere(
    const unsigned subdivision_level,
    const double perturbation_amplitude,
    const double rotation_radians
) {
    constexpr double phi = 1.6180339887498948482;
    std::vector<Vector3> vertices{
        {-1, phi, 0}, {1, phi, 0}, {-1, -phi, 0}, {1, -phi, 0},
        {0, -1, phi}, {0, 1, phi}, {0, -1, -phi}, {0, 1, -phi},
        {phi, 0, -1}, {phi, 0, 1}, {-phi, 0, -1}, {-phi, 0, 1},
    };
    for(auto& vertex : vertices) vertex = normalized(vertex);
    std::vector<std::array<unsigned, 3>> faces{
        {0,11,5}, {0,5,1}, {0,1,7}, {0,7,10}, {0,10,11},
        {1,5,9}, {5,11,4}, {11,10,2}, {10,7,6}, {7,1,8},
        {3,9,4}, {3,4,2}, {3,2,6}, {3,6,8}, {3,8,9},
        {4,9,5}, {2,4,11}, {6,2,10}, {8,6,7}, {9,8,1},
    };

    for(unsigned level = 0; level < subdivision_level; ++level) {
        std::map<std::pair<unsigned, unsigned>, unsigned> midpoint_ids;
        auto midpoint = [&](unsigned first, unsigned second) {
            if(first > second) std::swap(first, second);
            const auto key = std::make_pair(first, second);
            const auto found = midpoint_ids.find(key);
            if(found != midpoint_ids.end()) return found->second;
            const unsigned id = static_cast<unsigned>(vertices.size());
            vertices.push_back(normalized(scale(add(vertices[first], vertices[second]), 0.5)));
            midpoint_ids.emplace(key, id);
            return id;
        };
        std::vector<std::array<unsigned, 3>> refined;
        refined.reserve(faces.size() * 4);
        for(const auto& triangle : faces) {
            const unsigned ab = midpoint(triangle[0], triangle[1]);
            const unsigned bc = midpoint(triangle[1], triangle[2]);
            const unsigned ca = midpoint(triangle[2], triangle[0]);
            refined.push_back({triangle[0], ab, ca});
            refined.push_back({triangle[1], bc, ab});
            refined.push_back({triangle[2], ca, bc});
            refined.push_back({ab, bc, ca});
        }
        faces = std::move(refined);
    }

    mesh result;
    result.node_pos_lst.reserve(vertices.size() * 3);
    for(const auto& unit : vertices) {
        const double pattern = unit[0] * unit[1] + unit[1] * unit[2] + unit[2] * unit[0];
        const double radial_factor = 1.0 + perturbation_amplitude * pattern;
        const Vector3 point = rotate_z(scale(unit, kEquivalentRadius * radial_factor), rotation_radians);
        result.node_pos_lst.insert(result.node_pos_lst.end(), point.begin(), point.end());
    }
    result.face_point_ids.reserve(faces.size());
    for(const auto& triangle : faces) {
        result.face_point_ids.push_back({triangle[0], triangle[1], triangle[2]});
    }

    const auto measure = measure_mesh(result);
    const double current_volume = std::abs(measure.signed_volume);
    if(!(current_volume > 0.0) || !std::isfinite(current_volume)) {
        throw std::runtime_error("generated icosphere has invalid volume");
    }
    const double rescale = std::cbrt(kTargetVolume / current_volume);
    for(double& coordinate : result.node_pos_lst) coordinate *= rescale;
    return result;
}

cell_type_param_ptr make_myocardium_type(const double target_isoperimetric_ratio) {
    auto parameters = std::make_shared<cell_type_parameters>();
    parameters->name_ = "myocardium";
    parameters->global_type_id_ = 4;
    parameters->mass_density_ = 1.0;
    parameters->bulk_modulus_ = kBulkModulus;
    parameters->max_pressure_ = 100.0;
    parameters->initial_pressure_ = 0.0;
    parameters->area_elasticity_modulus_ = kAreaElasticityModulus;
    parameters->avg_division_vol_ = 1.0e30;
    parameters->std_division_vol_ = 0.0;
    parameters->avg_growth_rate_ = 0.0;
    parameters->std_growth_rate_ = 0.0;
    parameters->min_vol_ = 1.0e-12;
    parameters->angle_regularization_factor_ = 0.0;
    parameters->target_isoperimetric_ratio_ = target_isoperimetric_ratio;
    parameters->surface_coupling_max_curvature_ = 1.0e9;
    face_type_parameters face_parameters;
    face_parameters.name_ = "myocardium_surface";
    face_parameters.face_type_global_id_ = 4;
    face_parameters.surface_tension_ = kSurfaceTension;
    face_parameters.adherence_strength_ = 0.0;
    face_parameters.repulsion_strength_ = 0.0;
    face_parameters.bending_modulus_ = kBendingModulus;
    parameters->add_face_type(face_parameters);
    return parameters;
}

std::vector<double> nodal_areas(const cell& surface) {
    std::vector<double> result(surface.get_node_lst().size(), 0.0);
    for(const face& current_face : surface.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        for(const unsigned id : ids) result.at(id) += current_face.get_area() / 3.0;
    }
    return result;
}

double passive_energy(const cell& surface) {
    return static_cast<double>(surface.get_surface_tension_energy())
        + static_cast<double>(surface.get_membrane_elasticity_energy())
        + static_cast<double>(surface.get_bending_energy())
        + static_cast<double>(surface.get_pressure_energy());
}

CytoskeletonLoad cytoskeleton_load(
    const cell& surface,
    const RunConfig& config,
    const double load_fraction
) {
    CytoskeletonLoad result;
    result.nodal_forces.assign(surface.get_node_lst().size(), Vector3{});
    result.long_axis = rotate_z({1.0, 0.0, 0.0}, config.rotation_radians);
    result.transverse_axis = rotate_z({0.0, 1.0, 0.0}, config.rotation_radians);
    result.thickness_axis = {0.0, 0.0, 1.0};
    const double amplitude = config.cytoskeleton_enabled
        ? config.stress_amplitude * load_fraction : 0.0;
    result.stress = matrix_add(
        matrix_add(dyadic(result.long_axis, amplitude), dyadic(result.transverse_axis, -0.15 * amplitude)),
        dyadic(result.thickness_axis, -0.85 * amplitude)
    );

    for(const face& current_face : surface.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        const Vector3 normal = from_vec3(current_face.get_normal());
        const Vector3 stress_traction = matrix_vector(result.stress, normal);
        const Vector3 traction = scale(normal, dot(normal, stress_traction));
        const Vector3 face_force = scale(traction, current_face.get_area());
        for(const unsigned id : ids) {
            result.nodal_forces.at(id) = add(result.nodal_forces.at(id), scale(face_force, 1.0 / 3.0));
        }
    }

    // SimuCell3D's surface vertices have no in-plane cytoskeletal shear
    // elasticity.  Retain only the vertex-normal component of the active
    // traction so that tangential mesh drift is not mistaken for cell shape.
    for(std::size_t index = 0; index < result.nodal_forces.size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        const Vector3 normal = normalized(from_vec3(current_node.get_normal()));
        result.nodal_forces[index] = scale(normal, dot(normal, result.nodal_forces[index]));
    }

    // Remove discrete rigid translation and rotation introduced by projection
    // and remeshing.  This changes neither the prescribed deviatoric mode nor
    // the shape-driving component, but enforces a self-equilibrated free cell.
    std::vector<std::size_t> active_indices;
    Vector3 node_mean{};
    Vector3 projected_net_force{};
    for(std::size_t index = 0; index < result.nodal_forces.size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        active_indices.push_back(index);
        node_mean = add(node_mean, node_position(current_node));
        projected_net_force = add(projected_net_force, result.nodal_forces[index]);
    }
    if(active_indices.empty()) throw std::runtime_error("cytoskeleton load has no active vertices");
    node_mean = scale(node_mean, 1.0 / static_cast<double>(active_indices.size()));
    const Vector3 translation_correction = scale(
        projected_net_force,
        -1.0 / static_cast<double>(active_indices.size())
    );
    for(const std::size_t index : active_indices) {
        result.nodal_forces[index] = add(result.nodal_forces[index], translation_correction);
    }
    Vector3 projected_net_moment{};
    Matrix3 rotational_inertia{};
    for(const std::size_t index : active_indices) {
        const Vector3 arm = subtract(node_position(surface.get_node_lst()[index]), node_mean);
        projected_net_moment = add(projected_net_moment, cross(arm, result.nodal_forces[index]));
        const double radius_squared = dot(arm, arm);
        for(std::size_t row = 0; row < 3; ++row) {
            for(std::size_t column = 0; column < 3; ++column) {
                rotational_inertia[row][column] += (row == column ? radius_squared : 0.0)
                    - arm[row] * arm[column];
            }
        }
    }
    const Vector3 rotation_correction = solve_linear_system(
        rotational_inertia,
        scale(projected_net_moment, -1.0)
    );
    for(const std::size_t index : active_indices) {
        const Vector3 arm = subtract(node_position(surface.get_node_lst()[index]), node_mean);
        result.nodal_forces[index] = add(
            result.nodal_forces[index],
            cross(rotation_correction, arm)
        );
    }

    const Vector3 center = from_vec3(surface.get_centroid());
    Vector3 net_force{};
    Vector3 net_moment{};
    double force_scale = 0.0;
    double moment_scale = 0.0;
    for(std::size_t index = 0; index < result.nodal_forces.size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        const Vector3 force = result.nodal_forces[index];
        const Vector3 arm = subtract(node_position(current_node), center);
        const Vector3 moment = cross(arm, force);
        net_force = add(net_force, force);
        net_moment = add(net_moment, moment);
        force_scale += norm(force);
        moment_scale += norm(moment);
    }
    result.absolute_force_residual = norm(net_force);
    result.relative_force_residual = result.absolute_force_residual / std::max(force_scale, kTiny);
    result.absolute_moment_residual = norm(net_moment);
    result.relative_moment_residual = result.absolute_moment_residual / std::max(moment_scale, kTiny);
    return result;
}

std::vector<SurfaceVertexForce> as_surface_forces(
    const cell& surface,
    const std::vector<Vector3>& values
) {
    std::vector<SurfaceVertexForce> result;
    result.reserve(values.size());
    for(std::size_t index = 0; index < values.size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        result.push_back({current_node.get_persistent_id(), values[index]});
    }
    return result;
}

void reset_forces(cell& surface) {
    static_cast<void>(prl::cell_engine::reset_surface_forces(surface, surface.get_mesh_revision()));
}

std::vector<Vector3> capture_forces(const cell& surface) {
    std::vector<Vector3> result(surface.get_node_lst().size(), Vector3{});
    for(std::size_t index = 0; index < result.size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(current_node.is_used()) result[index] = node_force(current_node);
    }
    return result;
}

double minimum_triangle_angle_degrees(const cell& surface) {
    double minimum = std::numeric_limits<double>::infinity();
    for(const face& current_face : surface.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        const Vector3 a = node_position(surface.get_const_ref_node(ids[0]));
        const Vector3 b = node_position(surface.get_const_ref_node(ids[1]));
        const Vector3 c = node_position(surface.get_const_ref_node(ids[2]));
        const std::array<double, 3> lengths{
            norm(subtract(b, c)), norm(subtract(a, c)), norm(subtract(a, b))
        };
        for(std::size_t corner = 0; corner < 3; ++corner) {
            const double adjacent_1 = lengths[(corner + 1) % 3];
            const double adjacent_2 = lengths[(corner + 2) % 3];
            const double opposite = lengths[corner];
            const double cosine = std::clamp(
                (adjacent_1 * adjacent_1 + adjacent_2 * adjacent_2 - opposite * opposite)
                    / (2.0 * adjacent_1 * adjacent_2),
                -1.0,
                1.0
            );
            minimum = std::min(minimum, std::acos(cosine) * 180.0 / kPi);
        }
    }
    return minimum;
}

void write_faces_snapshot(
    const cell& surface,
    const unsigned snapshot_index,
    std::ofstream& stream
) {
    for(const face& current_face : surface.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        stream << snapshot_index << ',' << current_face.get_local_id() << ','
               << ids[0] << ',' << ids[1] << ',' << ids[2] << ','
               << surface.get_const_ref_node(ids[0]).get_persistent_id() << ','
               << surface.get_const_ref_node(ids[1]).get_persistent_id() << ','
               << surface.get_const_ref_node(ids[2]).get_persistent_id() << '\n';
    }
}

double write_snapshot(
    cell& surface,
    const RunConfig& config,
    const unsigned snapshot_index,
    const std::string& phase,
    const unsigned step,
    const double solver_coordinate,
    const double load_fraction,
    const double relaxation_fraction,
    std::ofstream& nodes_stream,
    double& max_cyt_force_residual,
    double& max_cyt_moment_residual
) {
    reset_forces(surface);
    surface.apply_internal_forces(0.0);
    const auto passive = capture_forces(surface);
    const auto cytoskeleton = cytoskeleton_load(surface, config, load_fraction);
    max_cyt_force_residual = std::max(max_cyt_force_residual, cytoskeleton.relative_force_residual);
    max_cyt_moment_residual = std::max(max_cyt_moment_residual, cytoskeleton.relative_moment_residual);
    const auto areas = nodal_areas(surface);
    double maximum_total_force = 0.0;
    nodes_stream << std::setprecision(17);
    for(std::size_t index = 0; index < surface.get_node_lst().size(); ++index) {
        const node& current_node = surface.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        const Vector3 position = node_position(current_node);
        const Vector3 total = add(passive[index], cytoskeleton.nodal_forces[index]);
        maximum_total_force = std::max(maximum_total_force, norm(total));
        nodes_stream
            << snapshot_index << ',' << phase << ',' << step << ',' << solver_coordinate << ','
            << load_fraction << ',' << relaxation_fraction << ',' << index << ','
            << current_node.get_persistent_id() << ','
            << position[0] << ',' << position[1] << ',' << position[2] << ','
            << areas[index] << ',' << current_node.get_curvature() << ',' << surface.get_pressure() << ','
            << passive[index][0] << ',' << passive[index][1] << ',' << passive[index][2] << ','
            << cytoskeleton.nodal_forces[index][0] << ','
            << cytoskeleton.nodal_forces[index][1] << ','
            << cytoskeleton.nodal_forces[index][2] << ','
            << total[0] << ',' << total[1] << ',' << total[2] << ','
            << norm(cytoskeleton.nodal_forces[index]) / std::max(areas[index], kTiny) << ','
            << norm(total) / std::max(areas[index], kTiny) << '\n';
        if(!finite(position) || !finite(total) || !std::isfinite(current_node.get_curvature())) {
            throw std::runtime_error("snapshot contains non-finite geometry or force field");
        }
    }
    reset_forces(surface);
    return maximum_total_force;
}

void write_metrics(
    const std::filesystem::path& path,
    const RunConfig& config,
    const double target_isoperimetric_ratio,
    const unsigned step_count,
    const double elapsed_seconds,
    const double max_volume_error,
    const double min_saved_triangle_angle,
    const double min_step_triangle_angle,
    const double max_cyt_force_residual,
    const double max_cyt_moment_residual,
    const double max_work_residual,
    const double peak_force,
    const double final_force,
    const double cumulative_cytoskeleton_work,
    const unsigned initial_face_count,
    const unsigned initial_node_count,
    const unsigned final_face_count,
    const unsigned final_node_count,
    const std::uint64_t remesh_revision_count,
    const Vector3& long_axis,
    const Vector3& transverse_axis,
    const Vector3& thickness_axis
) {
    std::ofstream stream(path);
    stream << std::setprecision(17);
    stream << "{\n"
           << "  \"schema_version\": 2,\n"
           << "  \"stage\": \"Z1-BIOFORM-MYO-A\",\n"
           << "  \"raw_execution_status\": \"completed\",\n"
           << "  \"condition\": \"" << config.condition << "\",\n"
           << "  \"kernel\": \"PRL-controlled SimuCell3D\",\n"
           << "  \"coordinate_semantics\": \"algorithmic_loading_and_relaxation_not_physical_time\",\n"
           << "  \"cell_count\": 1,\n"
           << "  \"requested_face_count\": " << config.face_count << ",\n"
           << "  \"initial_face_count\": " << initial_face_count << ",\n"
           << "  \"initial_node_count\": " << initial_node_count << ",\n"
           << "  \"final_face_count\": " << final_face_count << ",\n"
           << "  \"final_node_count\": " << final_node_count << ",\n"
           << "  \"snapshot_count\": 9,\n"
           << "  \"step_count\": " << step_count << ",\n"
           << "  \"time_step\": " << config.time_step << ",\n"
           << "  \"ramp_coordinate\": " << kRampCoordinate << ",\n"
           << "  \"hold_coordinate\": " << kHoldCoordinate << ",\n"
           << "  \"stress_amplitude\": " << config.stress_amplitude << ",\n"
           << "  \"cytoskeleton_enabled\": " << (config.cytoskeleton_enabled ? "true" : "false") << ",\n"
           << "  \"perturbed_initial_geometry\": " << (config.perturbed ? "true" : "false") << ",\n"
           << "  \"rotation_degrees\": " << config.rotation_radians * 180.0 / kPi << ",\n"
           << "  \"stress_principal_ratios\": [1.0, -0.15, -0.85],\n"
           << "  \"stress_trace\": 0.0,\n"
           << "  \"long_axis\": [" << long_axis[0] << ", " << long_axis[1] << ", " << long_axis[2] << "],\n"
           << "  \"transverse_axis\": [" << transverse_axis[0] << ", " << transverse_axis[1] << ", " << transverse_axis[2] << "],\n"
           << "  \"thickness_axis\": [" << thickness_axis[0] << ", " << thickness_axis[1] << ", " << thickness_axis[2] << "],\n"
           << "  \"target_volume\": " << kTargetVolume << ",\n"
           << "  \"target_isoperimetric_ratio\": " << target_isoperimetric_ratio << ",\n"
           << "  \"surface_tension\": " << kSurfaceTension << ",\n"
           << "  \"bending_modulus\": " << kBendingModulus << ",\n"
           << "  \"area_elasticity_modulus\": " << kAreaElasticityModulus << ",\n"
           << "  \"bulk_modulus\": " << kBulkModulus << ",\n"
           << "  \"surface_damping_density\": " << kSurfaceDampingDensity << ",\n"
           << "  \"reference_edge_shape_terms\": 0,\n"
           << "  \"reference_face_metric_terms\": 0,\n"
           << "  \"target_geometry_used\": false,\n"
           << "  \"dynamic_remeshing\": true,\n"
           << "  \"remesh_revision_count\": " << remesh_revision_count << ",\n"
           << "  \"max_volume_relative_error\": " << max_volume_error << ",\n"
           << "  \"minimum_saved_triangle_angle_deg\": " << min_saved_triangle_angle << ",\n"
           << "  \"minimum_step_triangle_angle_deg\": " << min_step_triangle_angle << ",\n"
           << "  \"max_cytoskeleton_relative_force_residual\": " << max_cyt_force_residual << ",\n"
           << "  \"max_cytoskeleton_relative_moment_residual\": " << max_cyt_moment_residual << ",\n"
           << "  \"max_work_dissipation_relative_residual\": " << max_work_residual << ",\n"
           << "  \"peak_free_node_total_force\": " << peak_force << ",\n"
           << "  \"final_free_node_total_force\": " << final_force << ",\n"
           << "  \"final_to_peak_free_force_ratio\": " << final_force / std::max(peak_force, kTiny) << ",\n"
           << "  \"cumulative_cytoskeleton_work\": " << cumulative_cytoskeleton_work << ",\n"
           << "  \"elapsed_seconds\": " << elapsed_seconds << "\n"
           << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        if(argc != 6) {
            throw std::invalid_argument(
                "usage: prl_ventricle_bioform_myo OUTPUT CONDITION FACE_COUNT DT STRESS_AMPLITUDE"
            );
        }
        const std::filesystem::path output_directory = std::filesystem::absolute(argv[1]);
        if(std::filesystem::exists(output_directory)) {
            throw std::runtime_error("create-only condition output already exists");
        }
        const RunConfig config = parse_config(
            argv[2],
            static_cast<unsigned>(std::stoul(argv[3])),
            std::stod(argv[4]),
            std::stod(argv[5])
        );
        std::filesystem::create_directories(output_directory);
        omp_set_num_threads(1);
        const auto started = std::chrono::steady_clock::now();

        const mesh reference_geometry = make_icosphere(config.subdivision_level, 0.0, config.rotation_radians);
        const MeshMeasure reference_measure = measure_mesh(reference_geometry);
        const double target_isoperimetric_ratio = std::pow(reference_measure.area, 3)
            / std::pow(std::abs(reference_measure.signed_volume), 2);
        const mesh initial_geometry = make_icosphere(
            config.subdivision_level,
            config.perturbed ? kPerturbationAmplitude : 0.0,
            config.rotation_radians
        );
        auto surface = std::make_shared<cell>(
            initial_geometry,
            0,
            make_myocardium_type(target_isoperimetric_ratio)
        );
        surface->initialize_cell_properties();
        surface->update_centroid();
        const double nominal_edge_length = std::sqrt(
            4.0 * surface->get_area()
            / (std::sqrt(3.0) * static_cast<double>(surface->get_nb_of_faces()))
        );
        local_mesh_refiner mesh_quality_refiner(
            0.45 * nominal_edge_length,
            1.60 * nominal_edge_length,
            true,
            nullptr,
            0.55
        );
        const auto initial_vertex_count = surface->get_nb_of_nodes();
        const auto initial_face_count = surface->get_nb_of_faces();
        const auto initial_mesh_revision = surface->get_mesh_revision();

        std::ofstream faces_stream(output_directory / "faces.csv");
        std::ofstream nodes_stream(output_directory / "nodes.csv");
        std::ofstream audit_stream(output_directory / "step_audits.csv");
        faces_stream << "snapshot_index,face_local_id,n1,n2,n3,p1,p2,p3\n";
        nodes_stream
            << "snapshot_index,phase,step,solver_coordinate,load_fraction,relaxation_fraction,"
            << "node_index,persistent_id,x,y,z,nodal_area,curvature,internal_pressure,"
            << "passive_fx,passive_fy,passive_fz,cytoskeleton_fx,cytoskeleton_fy,cytoskeleton_fz,"
            << "total_fx,total_fy,total_fz,cytoskeleton_traction,total_traction\n";
        audit_stream
            << "phase,step,solver_coordinate,load_fraction,relaxation_fraction,total_force_l2,"
            << "displacement_l2,total_force_work,viscous_dissipation,work_residual,relative_work_residual,"
            << "cytoskeleton_work_increment,passive_energy_before,passive_energy_after,area,volume,"
            << "minimum_face_area,cytoskeleton_force_residual,cytoskeleton_moment_residual\n";

        double max_volume_error = 0.0;
        double min_step_triangle_angle = minimum_triangle_angle_degrees(*surface);
        double min_saved_triangle_angle = std::numeric_limits<double>::infinity();
        double max_cyt_force_residual = 0.0;
        double max_cyt_moment_residual = 0.0;
        double max_work_residual = 0.0;
        double peak_force = 0.0;
        double final_force = 0.0;
        double cumulative_cytoskeleton_work = 0.0;
        unsigned step = 0;
        unsigned snapshot_index = 0;

        auto save = [&](const std::string& phase, const double coordinate, const double load, const double relaxation) {
            const unsigned current_snapshot_index = snapshot_index++;
            min_saved_triangle_angle = std::min(
                min_saved_triangle_angle,
                minimum_triangle_angle_degrees(*surface)
            );
            write_faces_snapshot(*surface, current_snapshot_index, faces_stream);
            final_force = write_snapshot(
                *surface,
                config,
                current_snapshot_index,
                phase,
                step,
                coordinate,
                load,
                relaxation,
                nodes_stream,
                max_cyt_force_residual,
                max_cyt_moment_residual
            );
            peak_force = std::max(peak_force, final_force);
        };

        auto advance = [&](const std::string& phase, const double coordinate, const double load, const double relaxation) {
            mesh_quality_refiner.refine_mesh(surface);
            reset_forces(*surface);
            surface->apply_internal_forces(0.0);
            const double energy_before = passive_energy(*surface);
            const auto passive = capture_forces(*surface);
            const auto cytoskeleton = cytoskeleton_load(*surface, config, load);
            max_cyt_force_residual = std::max(max_cyt_force_residual, cytoskeleton.relative_force_residual);
            max_cyt_moment_residual = std::max(max_cyt_moment_residual, cytoskeleton.relative_moment_residual);
            double current_max_force = 0.0;
            for(std::size_t index = 0; index < passive.size(); ++index) {
                current_max_force = std::max(
                    current_max_force,
                    norm(add(passive[index], cytoskeleton.nodal_forces[index]))
                );
            }
            peak_force = std::max(peak_force, current_max_force);
            std::vector<Vector3> positions_before(surface->get_node_lst().size(), Vector3{});
            for(std::size_t index = 0; index < positions_before.size(); ++index) {
                if(surface->get_node_lst()[index].is_used()) {
                    positions_before[index] = node_position(surface->get_node_lst()[index]);
                }
            }
            const auto audit = prl::cell_engine::advance_surface_overdamped(
                *surface,
                surface->get_mesh_revision(),
                config.time_step,
                SurfaceDampingLaw{
                    SurfaceDampingMeasure::barycentric_dual_area,
                    kSurfaceDampingDensity,
                },
                as_surface_forces(*surface, cytoskeleton.nodal_forces)
            );
            surface->update_centroid();
            double cytoskeleton_work_increment = 0.0;
            for(std::size_t index = 0; index < positions_before.size(); ++index) {
                if(!surface->get_node_lst()[index].is_used()) continue;
                cytoskeleton_work_increment += dot(
                    cytoskeleton.nodal_forces[index],
                    subtract(node_position(surface->get_node_lst()[index]), positions_before[index])
                );
            }
            cumulative_cytoskeleton_work += cytoskeleton_work_increment;
            reset_forces(*surface);
            surface->apply_internal_forces(0.0);
            const double energy_after = passive_energy(*surface);
            reset_forces(*surface);
            const double relative_work_residual = audit.work_dissipation_residual
                / std::max({std::abs(audit.total_force_work), std::abs(audit.viscous_dissipation), kTiny});
            max_work_residual = std::max(max_work_residual, relative_work_residual);
            max_volume_error = std::max(
                max_volume_error,
                std::abs(surface->get_volume() - kTargetVolume) / kTargetVolume
            );
            min_step_triangle_angle = std::min(
                min_step_triangle_angle,
                minimum_triangle_angle_degrees(*surface)
            );
            audit_stream << std::setprecision(17)
                << phase << ',' << step << ',' << coordinate << ',' << load << ',' << relaxation << ','
                << audit.total_force_l2_norm << ',' << audit.displacement_l2_norm << ','
                << audit.total_force_work << ',' << audit.viscous_dissipation << ','
                << audit.work_dissipation_residual << ',' << relative_work_residual << ','
                << cytoskeleton_work_increment << ',' << energy_before << ',' << energy_after << ','
                << audit.surface_area_after << ',' << audit.volume_after << ','
                << audit.minimum_face_area_after << ','
                << cytoskeleton.relative_force_residual << ','
                << cytoskeleton.relative_moment_residual << '\n';
            if(!(audit.minimum_face_area_after > 0.0) || !std::isfinite(audit.volume_after)) {
                throw std::runtime_error("invalid mesh geometry during relaxation");
            }
            if(max_volume_error > 0.05) {
                throw std::runtime_error("volume error exceeded 5 percent safety stop");
            }
        };

        save("initial", 0.0, 0.0, 0.0);
        for(unsigned quarter = 1; quarter <= 4; ++quarter) {
            const double quarter_end = kRampCoordinate * static_cast<double>(quarter) / 4.0;
            while(static_cast<double>(step) * config.time_step + 0.5 * config.time_step < quarter_end) {
                ++step;
                const double coordinate = static_cast<double>(step) * config.time_step;
                advance("ramp", coordinate, std::min(1.0, coordinate / kRampCoordinate), 0.0);
            }
            save("ramp", quarter_end, static_cast<double>(quarter) / 4.0, 0.0);
        }
        const unsigned ramp_steps = step;
        for(unsigned quarter = 1; quarter <= 4; ++quarter) {
            const double hold_end = kHoldCoordinate * static_cast<double>(quarter) / 4.0;
            while(static_cast<double>(step - ramp_steps) * config.time_step + 0.5 * config.time_step < hold_end) {
                ++step;
                const double hold_coordinate = static_cast<double>(step - ramp_steps) * config.time_step;
                advance(
                    "hold",
                    kRampCoordinate + hold_coordinate,
                    1.0,
                    std::min(1.0, hold_coordinate / kHoldCoordinate)
                );
            }
            save(
                "hold",
                kRampCoordinate + hold_end,
                1.0,
                static_cast<double>(quarter) / 4.0
            );
        }

        const auto final_load = cytoskeleton_load(*surface, config, 1.0);
        const auto final_vertex_count = surface->get_nb_of_nodes();
        const auto final_face_count = surface->get_nb_of_faces();
        const auto remesh_revision_count = surface->get_mesh_revision() - initial_mesh_revision;
        const double elapsed_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - started
        ).count();
        write_metrics(
            output_directory / "kernel_metrics.json",
            config,
            target_isoperimetric_ratio,
            step,
            elapsed_seconds,
            max_volume_error,
            min_saved_triangle_angle,
            min_step_triangle_angle,
            max_cyt_force_residual,
            max_cyt_moment_residual,
            max_work_residual,
            peak_force,
            final_force,
            cumulative_cytoskeleton_work,
            initial_face_count,
            initial_vertex_count,
            final_face_count,
            final_vertex_count,
            remesh_revision_count,
            final_load.long_axis,
            final_load.transverse_axis,
            final_load.thickness_axis
        );
        std::cout << std::setprecision(17)
                  << "Z1-BIOFORM-MYO-A raw condition complete\n"
                  << "condition=" << config.condition << '\n'
                  << "requested_faces=" << config.face_count << '\n'
                  << "final_faces=" << final_face_count << '\n'
                  << "steps=" << step << '\n'
                  << "max_volume_error=" << max_volume_error << '\n'
                  << "min_saved_triangle_angle=" << min_saved_triangle_angle << '\n'
                  << "min_step_triangle_angle=" << min_step_triangle_angle << '\n'
                  << "force_ratio=" << final_force / std::max(peak_force, kTiny) << '\n'
                  << "elapsed_seconds=" << elapsed_seconds << '\n';
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "Z1-BIOFORM-MYO-A failed: " << error.what() << '\n';
        return 1;
    }
}
