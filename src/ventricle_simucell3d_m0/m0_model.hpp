#pragma once

#include "cell.hpp"
#include "contact_face_face_via_coupling.hpp"
#include "custom_structures.hpp"

#include <array>
#include <algorithm>
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
#include <tuple>
#include <utility>
#include <vector>

#include <omp.h>

namespace prl::ventricle::m0 {

using Vector3 = std::array<double, 3>;

struct Body {
    cell_ptr surface;
    std::string role;
    std::string kinematic_mode{"deformable"};
    int grid_i{-1};
    int grid_j{-1};
    std::set<std::uint64_t> fixed_vertices;
    std::map<std::uint64_t, Vector3> initial_positions;
    std::vector<std::uint64_t> initial_vertex_ids;
    std::size_t initial_face_count{};
};

Vector3 add(const Vector3& first, const Vector3& second);
Vector3 subtract(const Vector3& first, const Vector3& second);
Vector3 scale(const Vector3& value, double factor);
double dot(const Vector3& first, const Vector3& second);
double norm(const Vector3& value);
Vector3 node_position(const node& current_node);
Vector3 node_force(const node& current_node);

cell_type_param_ptr make_cell_type(
    const std::string& name,
    short type_id,
    double surface_tension,
    double area_elasticity,
    double bending,
    double adhesion,
    double repulsion
);
Body make_body(
    const mesh& geometry,
    unsigned id,
    const std::string& role,
    const cell_type_param_ptr& type,
    int grid_i = -1,
    int grid_j = -1
);
std::vector<double> nodal_areas(const cell& surface);
void reset_forces(std::vector<Body>& bodies);
void assemble_contact(
    std::vector<Body>& bodies,
    contact_face_face_via_coupling& contact_model
);
global_simulation_parameters contact_parameters();
int run_m0(int argc, char** argv);

}  // namespace prl::ventricle::m0
