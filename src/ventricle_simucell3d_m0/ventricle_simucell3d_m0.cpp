#include "m0_model.hpp"
#include "contact_face_face_via_coupling.hpp"
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
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include <omp.h>

namespace prl::ventricle::m0 {
using prl::cell_engine::SurfaceDampingLaw;
using prl::cell_engine::SurfaceDampingMeasure;
using prl::cell_engine::SurfaceVertexForce;

constexpr double kContactCutoff = 0.35;
constexpr double kTimeStep = 0.01;
constexpr double kSurfaceDampingDensity = 1.0;
constexpr double kLumenPressure = 0.50;
constexpr double kActiveAmplitude = 0.035;
constexpr double kTiny = 1.0e-30;

struct LoadFields {
    std::vector<Vector3> active;
    std::vector<Vector3> pressure;
    std::vector<Vector3> reaction;
    std::vector<Vector3> contact;
    std::vector<Vector3> internal;
    std::vector<Vector3> total;
};

struct PressureFaceRecord {
    unsigned cell_id{};
    unsigned face_id{};
    double area{};
    Vector3 normal{};
    Vector3 force{};
};

struct ContactProbeMetrics {
    double force_norm_a{};
    double force_norm_b{};
    double absolute_balance_residual{};
    double relative_balance_residual{};
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

double norm(const Vector3& a) {
    return std::sqrt(dot(a, a));
}

Vector3 from_vec3(const vec3& value) {
    return {value.dx(), value.dy(), value.dz()};
}

bool finite(const Vector3& value) {
    return std::isfinite(value[0])
        && std::isfinite(value[1])
        && std::isfinite(value[2]);
}

Vector3 node_position(const node& current_node) {
    return from_vec3(current_node.pos());
}

Vector3 node_force(const node& current_node) {
    return from_vec3(current_node.force());
}

std::string csv_string(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for(const char character : value) {
        if(character == '"') escaped.push_back('"');
        escaped.push_back(character);
    }
    escaped.push_back('"');
    return escaped;
}

std::array<double, 3> normalized(const Vector3& value) {
    const double magnitude = norm(value);
    if(!(magnitude > 0.0) || !std::isfinite(magnitude)) {
        throw std::runtime_error("cannot normalize a zero or non-finite vector");
    }
    return scale(value, 1.0 / magnitude);
}

mesh make_icosphere(const Vector3& center, const Vector3& half_axes, const double exponent) {
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
    for(const auto& face_ids : faces) {
        const unsigned a = face_ids[0];
        const unsigned b = face_ids[1];
        const unsigned c = face_ids[2];
        const unsigned ab = midpoint(a, b);
        const unsigned bc = midpoint(b, c);
        const unsigned ca = midpoint(c, a);
        refined.push_back({a, ab, ca});
        refined.push_back({b, bc, ab});
        refined.push_back({c, ca, bc});
        refined.push_back({ab, bc, ca});
    }

    mesh result;
    result.node_pos_lst.reserve(vertices.size() * 3);
    const double power = 2.0 / exponent;
    for(const auto& unit : vertices) {
        Vector3 mapped{};
        for(std::size_t axis = 0; axis < 3; ++axis) {
            mapped[axis] = center[axis]
                + half_axes[axis] * std::copysign(std::pow(std::abs(unit[axis]), power), unit[axis]);
        }
        result.node_pos_lst.insert(result.node_pos_lst.end(), mapped.begin(), mapped.end());
    }
    for(const auto& triangle : refined) {
        result.face_point_ids.push_back({triangle[0], triangle[1], triangle[2]});
    }
    return result;
}

mesh make_closed_slab(
    const double half_x,
    const double half_y,
    const double half_z,
    const unsigned nx,
    const unsigned ny
) {
    if(nx < 2 || ny < 2) throw std::invalid_argument("slab grid must be at least 2 by 2");
    mesh result;
    const auto node_id = [nx, ny](const unsigned layer, const unsigned i, const unsigned j) {
        return layer * nx * ny + j * nx + i;
    };
    for(unsigned layer = 0; layer < 2; ++layer) {
        const double z = layer == 0 ? -half_z : half_z;
        for(unsigned j = 0; j < ny; ++j) {
            const double y = -half_y + 2.0 * half_y * static_cast<double>(j) / (ny - 1);
            for(unsigned i = 0; i < nx; ++i) {
                const double x = -half_x + 2.0 * half_x * static_cast<double>(i) / (nx - 1);
                result.node_pos_lst.insert(result.node_pos_lst.end(), {x, y, z});
            }
        }
    }

    auto add_face = [&](const unsigned a, const unsigned b, const unsigned c) {
        result.face_point_ids.push_back({a, b, c});
    };
    for(unsigned j = 0; j + 1 < ny; ++j) {
        for(unsigned i = 0; i + 1 < nx; ++i) {
            const unsigned ta = node_id(1, i, j);
            const unsigned tb = node_id(1, i + 1, j);
            const unsigned tc = node_id(1, i + 1, j + 1);
            const unsigned td = node_id(1, i, j + 1);
            add_face(ta, tb, tc);
            add_face(ta, tc, td);

            const unsigned ba = node_id(0, i, j);
            const unsigned bb = node_id(0, i + 1, j);
            const unsigned bc = node_id(0, i + 1, j + 1);
            const unsigned bd = node_id(0, i, j + 1);
            add_face(ba, bc, bb);
            add_face(ba, bd, bc);
        }
    }

    for(unsigned i = 0; i + 1 < nx; ++i) {
        const unsigned ba = node_id(0, i, 0);
        const unsigned bb = node_id(0, i + 1, 0);
        const unsigned ta = node_id(1, i, 0);
        const unsigned tb = node_id(1, i + 1, 0);
        add_face(ba, bb, tb);
        add_face(ba, tb, ta);

        const unsigned bma = node_id(0, i, ny - 1);
        const unsigned bmb = node_id(0, i + 1, ny - 1);
        const unsigned tma = node_id(1, i, ny - 1);
        const unsigned tmb = node_id(1, i + 1, ny - 1);
        add_face(bma, tma, tmb);
        add_face(bma, tmb, bmb);
    }
    for(unsigned j = 0; j + 1 < ny; ++j) {
        const unsigned ba = node_id(0, 0, j);
        const unsigned bb = node_id(0, 0, j + 1);
        const unsigned ta = node_id(1, 0, j);
        const unsigned tb = node_id(1, 0, j + 1);
        add_face(ba, ta, tb);
        add_face(ba, tb, bb);

        const unsigned bma = node_id(0, nx - 1, j);
        const unsigned bmb = node_id(0, nx - 1, j + 1);
        const unsigned tma = node_id(1, nx - 1, j);
        const unsigned tmb = node_id(1, nx - 1, j + 1);
        add_face(bma, bmb, tmb);
        add_face(bma, tmb, tma);
    }
    return result;
}

cell_type_param_ptr make_cell_type(
    const std::string& name,
    const short type_id,
    const double surface_tension,
    const double bending_modulus,
    const double area_modulus,
    const double bulk_modulus,
    const double repulsion_strength
) {
    auto parameters = std::make_shared<cell_type_parameters>();
    parameters->name_ = name;
    parameters->global_type_id_ = type_id;
    parameters->mass_density_ = 1.0;
    parameters->bulk_modulus_ = bulk_modulus;
    parameters->max_pressure_ = 100.0;
    parameters->initial_pressure_ = 0.0;
    parameters->area_elasticity_modulus_ = area_modulus;
    parameters->avg_division_vol_ = 1.0e30;
    parameters->std_division_vol_ = 0.0;
    parameters->avg_growth_rate_ = 0.0;
    parameters->std_growth_rate_ = 0.0;
    parameters->min_vol_ = 1.0e-12;
    parameters->angle_regularization_factor_ = 0.0;
    // Set from the first initialized body of each role so the scalar
    // area-volume homeostasis starts at the generated geometry.
    parameters->target_isoperimetric_ratio_ = 0.0;
    parameters->surface_coupling_max_curvature_ = 1.0e9;
    face_type_parameters face_parameters;
    face_parameters.name_ = name + "_surface";
    face_parameters.face_type_global_id_ = type_id;
    face_parameters.surface_tension_ = surface_tension;
    face_parameters.adherence_strength_ = 0.04;
    face_parameters.repulsion_strength_ = repulsion_strength;
    face_parameters.bending_modulus_ = bending_modulus;
    parameters->add_face_type(face_parameters);
    return parameters;
}

Body make_body(
    const mesh& geometry,
    const unsigned id,
    const std::string& role,
    const cell_type_param_ptr& type,
    const int grid_i,
    const int grid_j
) {
    Body result;
    result.surface = std::make_shared<cell>(geometry, id, type);
    result.surface->initialize_cell_properties();
    result.surface->update_centroid();
    if(!(type->target_isoperimetric_ratio_ > 0.0)) {
        const double initial_area = result.surface->get_area();
        const double initial_volume = result.surface->get_volume();
        type->target_isoperimetric_ratio_ = std::pow(initial_area, 3)
            / std::pow(initial_volume, 2);
    }
    result.role = role;
    result.grid_i = grid_i;
    result.grid_j = grid_j;
    result.initial_face_count = result.surface->get_nb_of_faces();
    for(const node& current_node : result.surface->get_node_lst()) {
        if(!current_node.is_used()) continue;
        result.initial_vertex_ids.push_back(current_node.get_persistent_id());
        result.initial_positions.emplace(current_node.get_persistent_id(), node_position(current_node));
    }
    return result;
}

std::vector<double> nodal_areas(const cell& surface) {
    std::vector<double> areas(surface.get_node_lst().size(), 0.0);
    for(const face& current_face : surface.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        for(const unsigned id : ids) areas.at(id) += current_face.get_area() / 3.0;
    }
    return areas;
}

std::array<double, 3> solve_symmetric_3x3(
    std::array<std::array<double, 3>, 3> matrix,
    std::array<double, 3> rhs
) {
    for(std::size_t pivot = 0; pivot < 3; ++pivot) {
        std::size_t selected = pivot;
        for(std::size_t row = pivot + 1; row < 3; ++row) {
            if(std::abs(matrix[row][pivot]) > std::abs(matrix[selected][pivot])) selected = row;
        }
        if(!(std::abs(matrix[selected][pivot]) > 1.0e-14)) {
            throw std::runtime_error("active-force rigid-mode projection is singular");
        }
        std::swap(matrix[pivot], matrix[selected]);
        std::swap(rhs[pivot], rhs[selected]);
        const double diagonal = matrix[pivot][pivot];
        for(std::size_t column = pivot; column < 3; ++column) matrix[pivot][column] /= diagonal;
        rhs[pivot] /= diagonal;
        for(std::size_t row = 0; row < 3; ++row) {
            if(row == pivot) continue;
            const double factor = matrix[row][pivot];
            for(std::size_t column = pivot; column < 3; ++column) {
                matrix[row][column] -= factor * matrix[pivot][column];
            }
            rhs[row] -= factor * rhs[pivot];
        }
    }
    return rhs;
}

std::vector<Vector3> active_forces(const Body& body, const double fraction) {
    const auto& nodes = body.surface->get_node_lst();
    std::vector<Vector3> forces(nodes.size(), Vector3{});
    if(body.role != "myocardium" || fraction == 0.0) return forces;
    const auto areas = nodal_areas(*body.surface);
    const Vector3 center = from_vec3(body.surface->get_centroid());
    double half_x = 0.0;
    for(const node& current_node : nodes) {
        if(current_node.is_used()) {
            half_x = std::max(half_x, std::abs(current_node.pos().dx() - center[0]));
        }
    }
    std::array<std::array<double, 3>, 3> gram{};
    std::array<double, 3> rhs{};
    for(std::size_t index = 0; index < nodes.size(); ++index) {
        if(!nodes[index].is_used()) continue;
        const Vector3 position = node_position(nodes[index]);
        const double y = position[1] - center[1];
        const double z = position[2] - center[2];
        const std::array<double, 3> basis{1.0, y, z};
        const double raw = kActiveAmplitude * fraction * areas[index]
            * std::tanh(3.0 * (position[0] - center[0]) / half_x);
        for(std::size_t row = 0; row < 3; ++row) {
            rhs[row] += basis[row] * raw;
            for(std::size_t column = 0; column < 3; ++column) {
                gram[row][column] += basis[row] * basis[column];
            }
        }
        forces[index][0] = raw;
    }
    const auto correction = solve_symmetric_3x3(gram, rhs);
    for(std::size_t index = 0; index < nodes.size(); ++index) {
        if(!nodes[index].is_used()) continue;
        const Vector3 position = node_position(nodes[index]);
        const double y = position[1] - center[1];
        const double z = position[2] - center[2];
        forces[index][0] -= correction[0] + correction[1] * y + correction[2] * z;
    }
    return forces;
}

std::pair<std::vector<Vector3>, std::vector<PressureFaceRecord>> pressure_forces(
    const Body& body,
    const double fraction
) {
    std::vector<Vector3> forces(body.surface->get_node_lst().size(), Vector3{});
    std::vector<PressureFaceRecord> records;
    if(body.role != "endocardium" || fraction == 0.0) return {forces, records};
    const double pressure = kLumenPressure * fraction;
    const double center_z = body.surface->get_centroid().dz();
    for(const face& current_face : body.surface->get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto ids = current_face.get_node_ids();
        const double face_center_z = (
            body.surface->get_const_ref_node(ids[0]).pos().dz()
            + body.surface->get_const_ref_node(ids[1]).pos().dz()
            + body.surface->get_const_ref_node(ids[2]).pos().dz()
        ) / 3.0;
        const Vector3 normal = from_vec3(current_face.get_normal());
        if(face_center_z <= center_z || normal[2] <= 0.0) continue;
        const Vector3 face_force = scale(normal, -pressure * current_face.get_area());
        for(const unsigned id : ids) forces[id] = add(forces[id], scale(face_force, 1.0 / 3.0));
        records.push_back({
            body.surface->get_id(),
            current_face.get_local_id(),
            current_face.get_area(),
            normal,
            face_force,
        });
    }
    return {forces, records};
}

void reset_forces(std::vector<Body>& bodies) {
    for(auto& body : bodies) {
        static_cast<void>(prl::cell_engine::reset_surface_forces(
            *body.surface,
            body.surface->get_mesh_revision()
        ));
    }
}

std::vector<std::vector<Vector3>> capture_forces(const std::vector<Body>& bodies) {
    std::vector<std::vector<Vector3>> result;
    result.reserve(bodies.size());
    for(const auto& body : bodies) {
        std::vector<Vector3> values(body.surface->get_node_lst().size(), Vector3{});
        for(std::size_t index = 0; index < values.size(); ++index) {
            const node& current_node = body.surface->get_node_lst()[index];
            if(current_node.is_used()) values[index] = node_force(current_node);
        }
        result.push_back(std::move(values));
    }
    return result;
}

void assemble_contact(
    std::vector<Body>& bodies,
    contact_face_face_via_coupling& contact_model
) {
    std::vector<cell_ptr> cells;
    cells.reserve(bodies.size());
    for(std::size_t index = 0; index < bodies.size(); ++index) {
        bodies[index].surface->set_local_id(static_cast<unsigned>(index));
        cells.push_back(bodies[index].surface);
    }
    contact_model.run(cells);
}

double active_force_residual(
    const Body& body,
    const std::vector<Vector3>& forces,
    double& moment_residual
) {
    Vector3 net{};
    Vector3 moment{};
    double force_scale = 0.0;
    double moment_scale = 0.0;
    const Vector3 center = from_vec3(body.surface->get_centroid());
    for(std::size_t index = 0; index < forces.size(); ++index) {
        const node& current_node = body.surface->get_node_lst()[index];
        if(!current_node.is_used()) continue;
        const Vector3 arm = subtract(node_position(current_node), center);
        const Vector3 local_moment = cross(arm, forces[index]);
        net = add(net, forces[index]);
        moment = add(moment, local_moment);
        force_scale += norm(forces[index]);
        moment_scale += norm(local_moment);
    }
    moment_residual = norm(moment) / std::max(moment_scale, kTiny);
    return norm(net) / std::max(force_scale, kTiny);
}

double pressure_integral_residual(
    const std::vector<Vector3>& nodal_pressure,
    const std::vector<PressureFaceRecord>& records
) {
    Vector3 actual{};
    Vector3 expected{};
    double scale_sum = 0.0;
    for(const auto& value : nodal_pressure) actual = add(actual, value);
    for(const auto& record : records) {
        expected = add(expected, record.force);
        scale_sum += norm(record.force);
    }
    return norm(subtract(actual, expected)) / std::max(scale_sum, kTiny);
}

std::vector<SurfaceVertexForce> constrained_additional_forces(
    const Body& body,
    const std::vector<Vector3>& active,
    const std::vector<Vector3>& pressure,
    std::vector<Vector3>& reaction
) {
    const auto& nodes = body.surface->get_node_lst();
    reaction.assign(nodes.size(), Vector3{});
    std::vector<SurfaceVertexForce> result;
    result.reserve(body.surface->get_nb_of_nodes());
    for(std::size_t index = 0; index < nodes.size(); ++index) {
        const node& current_node = nodes[index];
        if(!current_node.is_used()) continue;
        const Vector3 external = add(active[index], pressure[index]);
        Vector3 additional = external;
        if(body.fixed_vertices.count(current_node.get_persistent_id()) != 0) {
            reaction[index] = scale(add(node_force(current_node), external), -1.0);
            additional = add(external, reaction[index]);
        }
        result.push_back({current_node.get_persistent_id(), additional});
    }
    return result;
}

double minimum_surface_distance(const cell& first, const cell& second) {
    double minimum = std::numeric_limits<double>::infinity();
    for(const node& current_node : first.get_node_lst()) {
        if(!current_node.is_used()) continue;
        for(const face& current_face : second.get_face_lst()) {
            if(!current_face.is_used()) continue;
            const auto ids = current_face.get_node_ids();
            const auto distance = contact_model_abstract::compute_node_triangle_distance(
                current_node.pos(),
                second.get_const_ref_node(ids[0]).pos(),
                second.get_const_ref_node(ids[1]).pos(),
                second.get_const_ref_node(ids[2]).pos()
            ).first;
            minimum = std::min(minimum, std::sqrt(distance));
        }
    }
    return minimum;
}

std::vector<std::tuple<std::size_t, std::size_t, std::string, bool>> ledger_pairs(
    const std::vector<Body>& bodies
) {
    std::vector<std::tuple<std::size_t, std::size_t, std::string, bool>> result;
    std::size_t ecm_index = bodies.size();
    for(std::size_t index = 0; index < bodies.size(); ++index) {
        if(bodies[index].role == "ecm") ecm_index = index;
    }
    if(ecm_index == bodies.size()) throw std::runtime_error("ECM body is missing");
    for(std::size_t first = 0; first < bodies.size(); ++first) {
        for(std::size_t second = first + 1; second < bodies.size(); ++second) {
            const auto& a = bodies[first];
            const auto& b = bodies[second];
            if(a.role == b.role
               && a.role != "ecm"
               && std::abs(a.grid_i - b.grid_i) + std::abs(a.grid_j - b.grid_j) == 1) {
                result.emplace_back(first, second, "same_layer_neighbor", true);
            } else if(a.role == "ecm" || b.role == "ecm") {
                result.emplace_back(first, second, "cell_ecm", true);
            } else if(a.grid_i == b.grid_i && a.grid_j == b.grid_j) {
                result.emplace_back(first, second, "myocardium_endocardium", false);
            }
        }
    }
    return result;
}

ContactProbeMetrics run_contact_probe(
    std::vector<Body>& bodies,
    contact_face_face_via_coupling& contact_model,
    const std::filesystem::path& output_path
) {
    std::size_t ecm_index = bodies.size();
    std::size_t endocardium_index = bodies.size();
    for(std::size_t index = 0; index < bodies.size(); ++index) {
        if(bodies[index].role == "ecm") ecm_index = index;
        if(bodies[index].role == "endocardium"
           && bodies[index].grid_i == 1
           && bodies[index].grid_j == 1) endocardium_index = index;
    }
    if(ecm_index == bodies.size() || endocardium_index == bodies.size()) {
        throw std::runtime_error("contact probe bodies are missing");
    }
    // SimuCell3D derives nodal normals/curvatures during the internal-force
    // pass; the face-contact broad phase requires those normals to be ready.
    reset_forces(bodies);
    for(auto& body : bodies) body.surface->apply_internal_forces(0.0);
    reset_forces(bodies);
    std::vector<cell_ptr> pair{bodies[endocardium_index].surface, bodies[ecm_index].surface};
    pair[0]->set_local_id(0);
    pair[1]->set_local_id(1);
    contact_model.run(pair);

    std::ofstream stream(output_path);
    stream << "object,cell_id,role,node_index,persistent_id,fx,fy,fz\n";
    stream << std::setprecision(17);
    Vector3 sum_a{};
    Vector3 sum_b{};
    double norm_sum = 0.0;
    for(const std::size_t body_index : {endocardium_index, ecm_index}) {
        const auto& body = bodies[body_index];
        const std::string object = body_index == endocardium_index ? "a" : "b";
        for(std::size_t node_index = 0; node_index < body.surface->get_node_lst().size(); ++node_index) {
            const node& current_node = body.surface->get_node_lst()[node_index];
            if(!current_node.is_used()) continue;
            const Vector3 force = node_force(current_node);
            if(body_index == endocardium_index) sum_a = add(sum_a, force);
            else sum_b = add(sum_b, force);
            norm_sum += norm(force);
            stream << object << ',' << body.surface->get_id() << ',' << body.role << ','
                   << node_index << ',' << current_node.get_persistent_id() << ','
                   << force[0] << ',' << force[1] << ',' << force[2] << '\n';
        }
    }
    const Vector3 balance = add(sum_a, sum_b);
    ContactProbeMetrics metrics;
    metrics.force_norm_a = norm(sum_a);
    metrics.force_norm_b = norm(sum_b);
    metrics.absolute_balance_residual = norm(balance);
    metrics.relative_balance_residual = norm(balance) / std::max(norm_sum, kTiny);
    reset_forces(bodies);
    return metrics;
}

void assign_clamps(std::vector<Body>& bodies) {
    double global_min_x = std::numeric_limits<double>::infinity();
    double global_max_x = -std::numeric_limits<double>::infinity();
    for(const auto& body : bodies) {
        for(const node& current_node : body.surface->get_node_lst()) {
            if(!current_node.is_used()) continue;
            global_min_x = std::min(global_min_x, current_node.pos().dx());
            global_max_x = std::max(global_max_x, current_node.pos().dx());
        }
    }
    const double width = global_max_x - global_min_x;
    for(auto& body : bodies) {
        for(const node& current_node : body.surface->get_node_lst()) {
            if(!current_node.is_used()) continue;
            const double x = current_node.pos().dx();
            bool fixed = false;
            if(body.role == "ecm") {
                fixed = x <= global_min_x + 0.025 * width || x >= global_max_x - 0.025 * width;
            } else if(body.grid_i == 0) {
                fixed = x <= body.surface->get_centroid().dx() - 0.70 * 4.2;
            } else if(body.grid_i == 3) {
                fixed = x >= body.surface->get_centroid().dx() + 0.70 * 4.2;
            }
            if(fixed) body.fixed_vertices.insert(current_node.get_persistent_id());
        }
        if(!body.fixed_vertices.empty()) body.kinematic_mode = "deformable_with_fixed_vertices";
    }
}

void write_faces(const std::vector<Body>& bodies, const std::filesystem::path& path) {
    std::ofstream stream(path);
    stream << "cell_id,role,face_id,n1,n2,n3\n";
    for(const auto& body : bodies) {
        for(const face& current_face : body.surface->get_face_lst()) {
            if(!current_face.is_used()) continue;
            const auto ids = current_face.get_node_ids();
            stream << body.surface->get_id() << ',' << body.role << ','
                   << current_face.get_local_id() << ','
                   << ids[0] << ',' << ids[1] << ',' << ids[2] << '\n';
        }
    }
}

void append_contact_ledger(
    const std::vector<Body>& bodies,
    const double fraction,
    std::ofstream& stream,
    std::size_t& allowed_contact_count,
    std::size_t& forbidden_contact_count
) {
    for(const auto& item : ledger_pairs(bodies)) {
        const std::size_t first = std::get<0>(item);
        const std::size_t second = std::get<1>(item);
        const std::string& kind = std::get<2>(item);
        const bool allowed = std::get<3>(item);
        const double distance = std::min(
            minimum_surface_distance(*bodies[first].surface, *bodies[second].surface),
            minimum_surface_distance(*bodies[second].surface, *bodies[first].surface)
        );
        const bool within = distance <= kContactCutoff;
        if(within && allowed) ++allowed_contact_count;
        if(within && !allowed) ++forbidden_contact_count;
        stream << fraction << ','
               << bodies[first].surface->get_id() << ','
               << bodies[second].surface->get_id() << ','
               << bodies[first].role << ',' << bodies[second].role << ','
               << kind << ',' << (allowed ? 1 : 0) << ','
               << distance << ',' << (within ? 1 : 0) << '\n';
    }
}

void write_snapshot(
    std::vector<Body>& bodies,
    contact_face_face_via_coupling& contact_model,
    const double fraction,
    std::ofstream& nodes_stream,
    std::ofstream& loads_stream,
    std::ofstream& pressure_faces_stream,
    double& max_active_force_residual,
    double& max_active_moment_residual,
    double& max_pressure_residual
) {
    reset_forces(bodies);
    for(auto& body : bodies) body.surface->apply_internal_forces(0.0);
    reset_forces(bodies);
    assemble_contact(bodies, contact_model);
    const auto contact = capture_forces(bodies);
    for(auto& body : bodies) body.surface->apply_internal_forces(0.0);

    nodes_stream << std::setprecision(17);
    loads_stream << std::setprecision(17);
    pressure_faces_stream << std::setprecision(17);
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        auto& body = bodies[body_index];
        const auto active = active_forces(body, fraction);
        auto pressure_result = pressure_forces(body, fraction);
        const auto& pressure = pressure_result.first;
        for(const auto& record : pressure_result.second) {
            pressure_faces_stream
                << fraction << ',' << record.cell_id << ',' << record.face_id << ','
                << record.area << ',' << record.normal[0] << ',' << record.normal[1] << ','
                << record.normal[2] << ',' << record.force[0] << ',' << record.force[1] << ','
                << record.force[2] << '\n';
        }
        double moment_residual = 0.0;
        const double force_residual = active_force_residual(body, active, moment_residual);
        max_active_force_residual = std::max(max_active_force_residual, force_residual);
        max_active_moment_residual = std::max(max_active_moment_residual, moment_residual);
        if(body.role == "endocardium" && fraction > 0.0) {
            max_pressure_residual = std::max(
                max_pressure_residual,
                pressure_integral_residual(pressure, pressure_result.second)
            );
        }
        std::vector<Vector3> reaction;
        static_cast<void>(constrained_additional_forces(body, active, pressure, reaction));
        const auto areas = nodal_areas(*body.surface);
        const auto& nodes = body.surface->get_node_lst();
        for(std::size_t node_index = 0; node_index < nodes.size(); ++node_index) {
            const node& current_node = nodes[node_index];
            if(!current_node.is_used()) continue;
            const Vector3 position = node_position(current_node);
            const Vector3 preassembled = node_force(current_node);
            const Vector3 internal = subtract(preassembled, contact[body_index][node_index]);
            const Vector3 total = add(add(preassembled, active[node_index]), add(pressure[node_index], reaction[node_index]));
            const double traction = norm(contact[body_index][node_index]) / std::max(areas[node_index], kTiny);
            nodes_stream
                << fraction << ',' << body.surface->get_id() << ',' << body.role << ','
                << body.kinematic_mode << ',' << node_index << ','
                << current_node.get_persistent_id() << ','
                << position[0] << ',' << position[1] << ',' << position[2] << ','
                << current_node.get_curvature() << ',' << body.surface->get_pressure() << ','
                << (body.fixed_vertices.count(current_node.get_persistent_id()) ? 1 : 0) << ','
                << traction << '\n';
            loads_stream
                << fraction << ',' << body.surface->get_id() << ',' << body.role << ','
                << node_index << ',' << current_node.get_persistent_id() << ','
                << active[node_index][0] << ',' << active[node_index][1] << ',' << active[node_index][2] << ','
                << pressure[node_index][0] << ',' << pressure[node_index][1] << ',' << pressure[node_index][2] << ','
                << reaction[node_index][0] << ',' << reaction[node_index][1] << ',' << reaction[node_index][2] << ','
                << contact[body_index][node_index][0] << ',' << contact[body_index][node_index][1] << ',' << contact[body_index][node_index][2] << ','
                << internal[0] << ',' << internal[1] << ',' << internal[2] << ','
                << total[0] << ',' << total[1] << ',' << total[2] << '\n';
            if(!finite(position) || !finite(total) || !std::isfinite(current_node.get_curvature())) {
                throw std::runtime_error("snapshot contains a non-finite mechanical field");
            }
        }
    }
    reset_forces(bodies);
}

void advance_one_fraction(
    std::vector<Body>& bodies,
    contact_face_face_via_coupling& contact_model,
    const double fraction,
    std::ofstream& audits_stream,
    double& max_work_residual
) {
    reset_forces(bodies);
    for(auto& body : bodies) body.surface->apply_internal_forces(0.0);
    reset_forces(bodies);
    assemble_contact(bodies, contact_model);
    for(auto& body : bodies) body.surface->apply_internal_forces(0.0);
    for(auto& body : bodies) {
        const auto active = active_forces(body, fraction);
        const auto pressure = pressure_forces(body, fraction).first;
        std::vector<Vector3> reaction;
        const auto additional = constrained_additional_forces(body, active, pressure, reaction);
        const auto audit = prl::cell_engine::advance_surface_overdamped(
            *body.surface,
            body.surface->get_mesh_revision(),
            kTimeStep,
            SurfaceDampingLaw{
                SurfaceDampingMeasure::barycentric_dual_area,
                kSurfaceDampingDensity,
            },
            additional
        );
        body.surface->update_centroid();
        const double relative_work_residual = audit.work_dissipation_residual
            / std::max({std::abs(audit.total_force_work), std::abs(audit.viscous_dissipation), kTiny});
        max_work_residual = std::max(max_work_residual, relative_work_residual);
        audits_stream << std::setprecision(17)
            << fraction << ',' << body.surface->get_id() << ',' << body.role << ','
            << body.fixed_vertices.size() << ',' << audit.stepped_vertex_count << ','
            << audit.preassembled_force_l2_norm << ',' << audit.additional_force_l2_norm << ','
            << audit.total_force_l2_norm << ',' << audit.displacement_l2_norm << ','
            << audit.total_force_work << ',' << audit.viscous_dissipation << ','
            << audit.work_dissipation_residual << ',' << relative_work_residual << ','
            << audit.surface_area_after << ',' << audit.volume_after << ','
            << audit.minimum_face_area_after << '\n';
    }
}

double maximum_fixed_displacement(const std::vector<Body>& bodies) {
    double maximum = 0.0;
    for(const auto& body : bodies) {
        for(const node& current_node : body.surface->get_node_lst()) {
            if(!current_node.is_used()
               || body.fixed_vertices.count(current_node.get_persistent_id()) == 0) continue;
            maximum = std::max(
                maximum,
                norm(subtract(
                    node_position(current_node),
                    body.initial_positions.at(current_node.get_persistent_id())
                ))
            );
        }
    }
    return maximum;
}

double maximum_ecm_free_displacement(const std::vector<Body>& bodies) {
    double maximum = 0.0;
    for(const auto& body : bodies) {
        if(body.role != "ecm") continue;
        for(const node& current_node : body.surface->get_node_lst()) {
            if(!current_node.is_used()
               || body.fixed_vertices.count(current_node.get_persistent_id()) != 0) continue;
            maximum = std::max(
                maximum,
                norm(subtract(
                    node_position(current_node),
                    body.initial_positions.at(current_node.get_persistent_id())
                ))
            );
        }
    }
    return maximum;
}

bool topology_is_unchanged(const std::vector<Body>& bodies) {
    for(const auto& body : bodies) {
        if(body.surface->get_nb_of_faces() != body.initial_face_count) return false;
        std::vector<std::uint64_t> ids;
        for(const node& current_node : body.surface->get_node_lst()) {
            if(current_node.is_used()) ids.push_back(current_node.get_persistent_id());
        }
        if(ids != body.initial_vertex_ids) return false;
    }
    return true;
}

std::vector<Body> make_trilayer() {
    const auto myocardium_type = make_cell_type("myocardium", 4, 0.010, 0.0010, 0.020, 0.20, 0.16);
    const auto endocardium_type = make_cell_type("endocardium", 5, 0.008, 0.0008, 0.018, 0.18, 0.16);
    const auto ecm_type = make_cell_type("ecm", 1, 0.002, 0.0004, 0.010, 0.12, 0.20);
    const Vector3 myocardium_axes{4.2, 3.2, 2.4};
    const Vector3 endocardium_axes{4.2, 3.2, 1.35};
    constexpr double exponent = 3.2;
    constexpr double spacing_x = 8.15;
    constexpr double spacing_y = 6.15;
    constexpr double ecm_half_z = 0.80;
    constexpr double interface_overlap = 0.12;
    const double myocardium_z = -ecm_half_z - myocardium_axes[2] + interface_overlap;
    const double endocardium_z = ecm_half_z + endocardium_axes[2] - interface_overlap;

    std::vector<Body> bodies;
    bodies.reserve(33);
    unsigned next_id = 0;
    for(int j = 0; j < 4; ++j) {
        for(int i = 0; i < 4; ++i) {
            const double x = (static_cast<double>(i) - 1.5) * spacing_x;
            const double y = (static_cast<double>(j) - 1.5) * spacing_y;
            bodies.push_back(make_body(
                make_icosphere({x, y, myocardium_z}, myocardium_axes, exponent),
                next_id++, "myocardium", myocardium_type, i, j
            ));
        }
    }
    const double half_x = 1.5 * spacing_x + myocardium_axes[0] + 0.40;
    const double half_y = 1.5 * spacing_y + myocardium_axes[1] + 0.40;
    bodies.push_back(make_body(
        make_closed_slab(half_x, half_y, ecm_half_z, 9, 7),
        next_id++, "ecm", ecm_type
    ));
    for(int j = 0; j < 4; ++j) {
        for(int i = 0; i < 4; ++i) {
            const double x = (static_cast<double>(i) - 1.5) * spacing_x;
            const double y = (static_cast<double>(j) - 1.5) * spacing_y;
            bodies.push_back(make_body(
                make_icosphere({x, y, endocardium_z}, endocardium_axes, exponent),
                next_id++, "endocardium", endocardium_type, i, j
            ));
        }
    }
    assign_clamps(bodies);
    for(std::size_t index = 0; index < bodies.size(); ++index) {
        bodies[index].surface->set_local_id(static_cast<unsigned>(index));
    }
    return bodies;
}

global_simulation_parameters contact_parameters() {
    global_simulation_parameters parameters;
    parameters.min_edge_len_ = 0.40;
    parameters.contact_cutoff_adhesion_ = kContactCutoff;
    parameters.contact_cutoff_repulsion_ = kContactCutoff;
    return parameters;
}

void write_metrics(
    const std::filesystem::path& path,
    const double elapsed_seconds,
    const ContactProbeMetrics& contact_probe,
    const double max_active_force_residual,
    const double max_active_moment_residual,
    const double max_pressure_residual,
    const double max_work_residual,
    const double max_fixed_displacement,
    const double max_ecm_displacement,
    const bool topology_unchanged,
    const std::size_t allowed_contact_count,
    const std::size_t forbidden_contact_count,
    const std::size_t node_count,
    const std::size_t face_count
) {
    std::ofstream stream(path);
    stream << std::setprecision(17);
    stream << "{\n"
           << "  \"schema_version\": 1,\n"
           << "  \"stage\": \"Z1-TF2-M0\",\n"
           << "  \"kernel\": \"PRL-controlled SimuCell3D\",\n"
           << "  \"coordinate_semantics\": \"algorithmic_continuation_not_physical_time\",\n"
           << "  \"body_count\": 33,\n"
           << "  \"myocardium_count\": 16,\n"
           << "  \"ecm_count\": 1,\n"
           << "  \"endocardium_count\": 16,\n"
           << "  \"snapshot_count\": 5,\n"
           << "  \"node_count\": " << node_count << ",\n"
           << "  \"face_count\": " << face_count << ",\n"
           << "  \"reference_edge_shape_terms\": 0,\n"
           << "  \"ecm_kinematic_mode\": \"deformable_with_fixed_vertices\",\n"
           << "  \"fixed_topology\": true,\n"
           << "  \"topology_unchanged\": " << (topology_unchanged ? "true" : "false") << ",\n"
           << "  \"allowed_contacts_within_cutoff\": " << allowed_contact_count << ",\n"
           << "  \"forbidden_contacts_within_cutoff\": " << forbidden_contact_count << ",\n"
           << "  \"contact_probe_force_norm_a\": " << contact_probe.force_norm_a << ",\n"
           << "  \"contact_probe_force_norm_b\": " << contact_probe.force_norm_b << ",\n"
           << "  \"contact_probe_absolute_balance_residual\": " << contact_probe.absolute_balance_residual << ",\n"
           << "  \"contact_probe_relative_balance_residual\": " << contact_probe.relative_balance_residual << ",\n"
           << "  \"max_active_net_force_relative_residual\": " << max_active_force_residual << ",\n"
           << "  \"max_active_net_moment_relative_residual\": " << max_active_moment_residual << ",\n"
           << "  \"max_pressure_integral_relative_residual\": " << max_pressure_residual << ",\n"
           << "  \"max_work_dissipation_relative_residual\": " << max_work_residual << ",\n"
           << "  \"max_fixed_vertex_displacement\": " << max_fixed_displacement << ",\n"
           << "  \"max_ecm_free_vertex_displacement\": " << max_ecm_displacement << ",\n"
           << "  \"contact_cutoff\": " << kContactCutoff << ",\n"
           << "  \"lumen_pressure_at_fraction_1\": " << kLumenPressure << ",\n"
           << "  \"active_amplitude_at_fraction_1\": " << kActiveAmplitude << ",\n"
           << "  \"time_step_per_continuation_increment\": " << kTimeStep << ",\n"
           << "  \"surface_damping_density\": " << kSurfaceDampingDensity << ",\n"
           << "  \"elapsed_seconds\": " << elapsed_seconds << "\n"
           << "}\n";
}

int run_m0(int argc, char** argv) {
    try {
        if(argc != 2) {
            throw std::invalid_argument("usage: prl_ventricle_simucell3d_m0 OUTPUT_DIRECTORY");
        }
        const auto started = std::chrono::steady_clock::now();
        const std::filesystem::path output_directory = std::filesystem::absolute(argv[1]);
        std::filesystem::create_directories(output_directory);
        omp_set_num_threads(4);

        auto bodies = make_trilayer();
        contact_face_face_via_coupling contact_model(contact_parameters());
        const auto contact_probe = run_contact_probe(
            bodies,
            contact_model,
            output_directory / "contact_probe_forces.csv"
        );

        write_faces(bodies, output_directory / "faces.csv");
        std::ofstream nodes_stream(output_directory / "nodes.csv");
        std::ofstream loads_stream(output_directory / "loads.csv");
        std::ofstream pressure_faces_stream(output_directory / "pressure_faces.csv");
        std::ofstream audits_stream(output_directory / "step_audits.csv");
        std::ofstream ledger_stream(output_directory / "contact_ledger.csv");
        nodes_stream << "fraction,cell_id,role,kinematic_mode,node_index,persistent_id,x,y,z,curvature,internal_pressure,fixed,contact_traction\n";
        loads_stream << "fraction,cell_id,role,node_index,persistent_id,active_fx,active_fy,active_fz,pressure_fx,pressure_fy,pressure_fz,reaction_fx,reaction_fy,reaction_fz,contact_fx,contact_fy,contact_fz,internal_fx,internal_fy,internal_fz,total_fx,total_fy,total_fz\n";
        pressure_faces_stream << "fraction,cell_id,face_id,area,nx,ny,nz,fx,fy,fz\n";
        audits_stream << "fraction,cell_id,role,fixed_vertex_count,stepped_vertex_count,preassembled_force_l2,additional_force_l2,total_force_l2,displacement_l2,total_force_work,viscous_dissipation,work_residual,relative_work_residual,area_after,volume_after,minimum_face_area_after\n";
        ledger_stream << "fraction,cell_a,cell_b,role_a,role_b,pair_kind,allowed,min_surface_distance,within_cutoff\n";
        ledger_stream << std::setprecision(17);

        double max_active_force_residual = 0.0;
        double max_active_moment_residual = 0.0;
        double max_pressure_residual = 0.0;
        double max_work_residual = 0.0;
        std::size_t allowed_contact_count = 0;
        std::size_t forbidden_contact_count = 0;
        const std::array<double, 5> fractions{0.0, 0.25, 0.50, 0.75, 1.0};
        for(std::size_t snapshot = 0; snapshot < fractions.size(); ++snapshot) {
            const double fraction = fractions[snapshot];
            if(snapshot > 0) {
                advance_one_fraction(
                    bodies,
                    contact_model,
                    fraction,
                    audits_stream,
                    max_work_residual
                );
            }
            write_snapshot(
                bodies,
                contact_model,
                fraction,
                nodes_stream,
                loads_stream,
                pressure_faces_stream,
                max_active_force_residual,
                max_active_moment_residual,
                max_pressure_residual
            );
            append_contact_ledger(
                bodies,
                fraction,
                ledger_stream,
                allowed_contact_count,
                forbidden_contact_count
            );
        }

        std::size_t node_count = 0;
        std::size_t face_count = 0;
        for(const auto& body : bodies) {
            node_count += body.surface->get_nb_of_nodes();
            face_count += body.surface->get_nb_of_faces();
        }
        const double fixed_displacement = maximum_fixed_displacement(bodies);
        const double ecm_displacement = maximum_ecm_free_displacement(bodies);
        const bool unchanged_topology = topology_is_unchanged(bodies);
        const double elapsed = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - started
        ).count();
        write_metrics(
            output_directory / "kernel_metrics.json",
            elapsed,
            contact_probe,
            max_active_force_residual,
            max_active_moment_residual,
            max_pressure_residual,
            max_work_residual,
            fixed_displacement,
            ecm_displacement,
            unchanged_topology,
            allowed_contact_count,
            forbidden_contact_count,
            node_count,
            face_count
        );
        std::cout << std::setprecision(17)
                  << "Z1-TF2-M0 raw execution complete\n"
                  << "contact_balance=" << contact_probe.relative_balance_residual << '\n'
                  << "pressure_integral=" << max_pressure_residual << '\n'
                  << "active_force=" << max_active_force_residual << '\n'
                  << "active_moment=" << max_active_moment_residual << '\n'
                  << "work_dissipation=" << max_work_residual << '\n'
                  << "fixed_displacement=" << fixed_displacement << '\n'
                  << "ecm_displacement=" << ecm_displacement << '\n'
                  << "elapsed_seconds=" << elapsed << '\n';
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "Z1-TF2-M0 failed: " << error.what() << '\n';
        return 1;
    }
}

} // namespace prl::ventricle::m0
