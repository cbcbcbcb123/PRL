#pragma once

#include "cell.hpp"
#include "custom_structures.hpp"
#include "prl_cell_engine/cell_surface_force.hpp"

#include <array>
#include <algorithm>
#include <chrono>
#include <cmath>
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

namespace prl::ventricle::bioform {

using Vector3 = std::array<double, 3>;
using Matrix3 = std::array<std::array<double, 3>, 3>;
using Vector6 = std::array<double, 6>;
using Matrix6 = std::array<std::array<double, 6>, 6>;
using prl::cell_engine::SurfaceDampingLaw;
using prl::cell_engine::SurfaceDampingMeasure;
using prl::cell_engine::SurfaceVertexForce;

inline constexpr double kPi = 3.1415926535897932384626433832795;
inline constexpr double kTargetVolume = 167.875410364543;
inline constexpr double kTiny = 1.0e-30;

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
    double normal_correction_l2{};
};

struct ShapeVelocityProjection {
    std::vector<Vector3> effective_total_forces;
    std::vector<Vector3> integrator_additional_forces;
    Vector3 removed_translation_velocity{};
    Vector3 removed_angular_velocity{};
    double maximum_shape_speed{};
    double weighted_translation_residual{};
    double weighted_rotation_residual{};
    double relative_translation_residual{};
    double relative_rotation_residual{};
    double physical_net_force{};
    double physical_net_moment{};
};

Vector3 add(const Vector3& first, const Vector3& second);
Vector3 subtract(const Vector3& first, const Vector3& second);
Vector3 scale(const Vector3& value, double factor);
double dot(const Vector3& first, const Vector3& second);
double norm(const Vector3& value);
Vector3 node_position(const node& current_node);
Vector3 node_force(const node& current_node);

RunConfig parse_config(
    const std::string& condition,
    unsigned face_count,
    double time_step,
    double stress_amplitude
);
MeshMeasure measure_mesh(const mesh& geometry);
mesh make_icosphere(
    unsigned subdivision_level,
    double perturbation_amplitude,
    double rotation_radians
);
cell_type_param_ptr make_myocardium_type(double target_isoperimetric_ratio);
std::vector<double> nodal_areas(const cell& surface);
double passive_energy(const cell& surface);
CytoskeletonLoad cytoskeleton_load(
    const cell& surface,
    const RunConfig& config,
    double load_fraction
);
std::vector<SurfaceVertexForce> as_surface_forces(
    const cell& surface,
    const std::vector<Vector3>& values
);
void reset_forces(cell& surface);
std::vector<Vector3> capture_forces(const cell& surface);
double minimum_edge_length(const cell& surface);
ShapeVelocityProjection project_shape_velocity(
    const cell& surface,
    const std::vector<Vector3>& passive,
    const std::vector<Vector3>& active
);
double choose_adaptive_substep(
    double remaining_step,
    double shortest_edge,
    double maximum_speed
);
double minimum_triangle_angle_degrees(const cell& surface);
int run_bioform_v03(int argc, char** argv);

}  // namespace prl::ventricle::bioform
