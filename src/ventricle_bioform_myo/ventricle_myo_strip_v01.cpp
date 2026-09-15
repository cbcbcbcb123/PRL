#define main prl_embedded_bioform_myo_v03_main
#include "ventricle_bioform_myo_v03.cpp"
#undef main

#include <sstream>

namespace {

constexpr std::size_t kStripCellCount = 5;
constexpr std::size_t kCenterCell = 2;
constexpr unsigned kFrozenSnapshot = 8;
constexpr double kInterfaceGap = 0.20;
constexpr double kCapRatio = 0.88;
constexpr double kShapeStress = 0.060;
constexpr double kContractionStiffness = 0.18;
constexpr double kJunctionStiffness = 0.80;
constexpr double kStripDampingDensity = 1.0;
constexpr double kStripMotionFraction = 0.08;

struct StripConfig {
    std::string condition;
    std::string boundary_mode{"ISOMETRIC"};
    std::filesystem::path input_nodes;
    std::filesystem::path input_faces;
    double requested_step{};
    double contraction_strain{};
    double support_stiffness{};
    unsigned settle_steps{};
    unsigned ramp_steps_per_segment{};
    unsigned hold_steps_per_segment{};
    bool junctions_enabled{true};
    bool boundary_mode_explicit{false};
};

struct StripBody {
    std::shared_ptr<cell> surface;
    std::vector<Vector3> initial_positions;
    std::vector<std::array<bool, 3>> fixed_axes;
    std::vector<bool> axial_support;
};

struct MaterialSpring {
    std::size_t body_a{};
    std::size_t node_a{};
    std::size_t body_b{};
    std::size_t node_b{};
    double rest_length{};
    double stiffness{};
    int interface_id{-1};
};

using ForceField = std::vector<std::vector<Vector3>>;

struct StripAssembly {
    ForceField passive;
    ForceField shape;
    ForceField contraction;
    ForceField adhesion;
    ForceField support;
    ForceField reaction;
    ForceField total;
    double contraction_energy{};
    double adhesion_energy{};
    double support_energy{};
    double maximum_free_force{};
    double junction_balance_residual{};
};

std::vector<std::string> split_plain_csv(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream stream(line);
    std::string value;
    while(std::getline(stream, value, ',')) fields.push_back(value);
    return fields;
}

mesh load_frozen_mesh(
    const std::filesystem::path& nodes_path,
    const std::filesystem::path& faces_path
) {
    std::ifstream nodes_stream(nodes_path);
    std::ifstream faces_stream(faces_path);
    if(!nodes_stream || !faces_stream) throw std::runtime_error("cannot open frozen myocardial mesh CSV files");
    std::string line;
    std::getline(nodes_stream, line);
    std::map<unsigned, Vector3> points;
    while(std::getline(nodes_stream, line)) {
        const auto fields = split_plain_csv(line);
        if(fields.size() < 11 || static_cast<unsigned>(std::stoul(fields[0])) != kFrozenSnapshot) continue;
        points[static_cast<unsigned>(std::stoul(fields[6]))] = {
            std::stod(fields[8]), std::stod(fields[9]), std::stod(fields[10])
        };
    }
    std::getline(faces_stream, line);
    std::vector<std::vector<unsigned>> triangles;
    while(std::getline(faces_stream, line)) {
        const auto fields = split_plain_csv(line);
        if(fields.size() < 5 || static_cast<unsigned>(std::stoul(fields[0])) != kFrozenSnapshot) continue;
        triangles.push_back({
            static_cast<unsigned>(std::stoul(fields[2])),
            static_cast<unsigned>(std::stoul(fields[3])),
            static_cast<unsigned>(std::stoul(fields[4]))
        });
    }
    if(points.size() != 162 || triangles.size() != 320) {
        throw std::runtime_error("frozen myocardial snapshot must contain 162 nodes and 320 faces");
    }
    mesh result;
    result.node_pos_lst.resize(points.size() * 3);
    for(std::size_t index = 0; index < points.size(); ++index) {
        const auto found = points.find(static_cast<unsigned>(index));
        if(found == points.end()) throw std::runtime_error("frozen myocardial node ids are not contiguous");
        for(std::size_t axis = 0; axis < 3; ++axis) result.node_pos_lst[3 * index + axis] = found->second[axis];
    }
    result.face_point_ids = std::move(triangles);
    return result;
}

std::vector<std::size_t> cap_nodes(const mesh& base, const bool positive) {
    double extreme = positive ? -std::numeric_limits<double>::infinity()
                              : std::numeric_limits<double>::infinity();
    for(std::size_t index = 0; index < base.node_pos_lst.size() / 3; ++index) {
        const double x = base.node_pos_lst[3 * index];
        extreme = positive ? std::max(extreme, x) : std::min(extreme, x);
    }
    const double threshold = kCapRatio * std::abs(extreme);
    std::vector<std::size_t> result;
    for(std::size_t index = 0; index < base.node_pos_lst.size() / 3; ++index) {
        const double x = base.node_pos_lst[3 * index];
        if((positive && x >= threshold) || (!positive && x <= -threshold)) result.push_back(index);
    }
    if(result.empty()) throw std::runtime_error("empty material end cap");
    return result;
}

std::vector<std::pair<std::size_t, std::size_t>> match_caps(
    const mesh& base,
    const std::vector<std::size_t>& right,
    const std::vector<std::size_t>& left
) {
    if(right.size() != left.size()) throw std::runtime_error("end caps do not have equal node counts");
    std::set<std::size_t> available(left.begin(), left.end());
    std::vector<std::pair<std::size_t, std::size_t>> result;
    for(const std::size_t right_id : right) {
        std::size_t best = *available.begin();
        double best_distance = std::numeric_limits<double>::infinity();
        const double y = base.node_pos_lst[3 * right_id + 1];
        const double z = base.node_pos_lst[3 * right_id + 2];
        for(const std::size_t left_id : available) {
            const double dy = y - base.node_pos_lst[3 * left_id + 1];
            const double dz = z - base.node_pos_lst[3 * left_id + 2];
            const double squared = dy * dy + dz * dz;
            if(squared < best_distance) {
                best_distance = squared;
                best = left_id;
            }
        }
        result.emplace_back(right_id, best);
        available.erase(best);
    }
    return result;
}

StripConfig parse_strip_config(int argc, char** argv) {
    if(argc != 10 && argc != 12) {
        throw std::invalid_argument(
            "usage: prl_ventricle_myo_strip_v01 OUTPUT CONDITION INPUT_NODES INPUT_FACES DT EPS SETTLE_STEPS RAMP_STEPS HOLD_STEPS [BOUNDARY_MODE SUPPORT_STIFFNESS]"
        );
    }
    StripConfig config;
    config.condition = argv[2];
    const std::set<std::string> allowed{"PASSIVE", "SYNC", "CENTER", "CENTER_NO_LINK"};
    if(allowed.count(config.condition) == 0) throw std::invalid_argument("unknown strip condition");
    config.input_nodes = std::filesystem::absolute(argv[3]);
    config.input_faces = std::filesystem::absolute(argv[4]);
    config.requested_step = std::stod(argv[5]);
    config.contraction_strain = std::stod(argv[6]);
    config.settle_steps = static_cast<unsigned>(std::stoul(argv[7]));
    config.ramp_steps_per_segment = static_cast<unsigned>(std::stoul(argv[8]));
    config.hold_steps_per_segment = static_cast<unsigned>(std::stoul(argv[9]));
    if(argc == 12) {
        config.boundary_mode = argv[10];
        config.support_stiffness = std::stod(argv[11]);
        config.boundary_mode_explicit = true;
    }
    config.junctions_enabled = config.condition != "CENTER_NO_LINK";
    const std::set<std::string> allowed_boundaries{"ISOMETRIC", "COMPLIANT", "FREE_LOW_LOAD"};
    if(allowed_boundaries.count(config.boundary_mode) == 0) {
        throw std::invalid_argument("unknown strip boundary mode");
    }
    if(!(config.requested_step > 0.0) || !(config.contraction_strain >= 0.0)
       || config.contraction_strain > 0.20 || config.ramp_steps_per_segment == 0
       || config.hold_steps_per_segment == 0 || !(config.support_stiffness >= 0.0)) {
        throw std::invalid_argument("inadmissible strip integration parameter");
    }
    if((config.boundary_mode == "COMPLIANT") != (config.support_stiffness > 0.0)) {
        throw std::invalid_argument("support stiffness must be positive only for COMPLIANT boundary mode");
    }
    return config;
}

double activation_value(const double phase) {
    const double sine = std::sin(kPi * phase);
    return sine * sine;
}

double cell_activation(const StripConfig& config, const std::size_t body, const double phase) {
    if(config.condition == "PASSIVE") return 0.0;
    if(config.condition == "SYNC") return activation_value(phase);
    return body == kCenterCell ? activation_value(phase) : 0.0;
}

ForceField zero_field(const std::vector<StripBody>& bodies) {
    ForceField result;
    for(const auto& body : bodies) result.emplace_back(body.surface->get_node_lst().size(), Vector3{});
    return result;
}

void add_spring_force(
    const MaterialSpring& spring,
    const double target_length,
    const std::vector<StripBody>& bodies,
    ForceField& field,
    double& energy,
    double& balance_numerator,
    double& balance_denominator
) {
    const Vector3 first = node_position(bodies[spring.body_a].surface->get_node_lst()[spring.node_a]);
    const Vector3 second = node_position(bodies[spring.body_b].surface->get_node_lst()[spring.node_b]);
    const Vector3 delta = subtract(second, first);
    const double length = norm(delta);
    if(!(length > kTiny) || !std::isfinite(length)) throw std::runtime_error("collapsed material spring");
    const double extension = length - target_length;
    const Vector3 force = scale(delta, spring.stiffness * extension / length);
    field[spring.body_a][spring.node_a] = add(field[spring.body_a][spring.node_a], force);
    field[spring.body_b][spring.node_b] = subtract(field[spring.body_b][spring.node_b], force);
    energy += 0.5 * spring.stiffness * extension * extension;
    balance_numerator += norm(add(force, scale(force, -1.0)));
    balance_denominator += 2.0 * norm(force);
}

StripAssembly assemble_strip(
    std::vector<StripBody>& bodies,
    const StripConfig& config,
    const RunConfig& shape_config,
    const std::vector<MaterialSpring>& contractile,
    const std::vector<MaterialSpring>& junctions,
    const double phase
) {
    StripAssembly result;
    result.passive = zero_field(bodies);
    result.shape = zero_field(bodies);
    result.contraction = zero_field(bodies);
    result.adhesion = zero_field(bodies);
    result.support = zero_field(bodies);
    result.reaction = zero_field(bodies);
    result.total = zero_field(bodies);
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        auto& surface = *bodies[body_index].surface;
        static_cast<void>(prl::cell_engine::refresh_surface_geometry(surface, surface.get_mesh_revision()));
        reset_forces(surface);
        surface.apply_internal_forces(0.0);
        result.passive[body_index] = capture_forces(surface);
        const auto raw_shape = cytoskeleton_load(surface, shape_config, 1.0);
        const std::vector<Vector3> zeros(surface.get_node_lst().size(), Vector3{});
        result.shape[body_index] = project_shape_velocity(surface, zeros, raw_shape.nodal_forces).effective_total_forces;
    }
    double contraction_balance = 0.0;
    double contraction_scale = 0.0;
    for(const auto& spring : contractile) {
        const double activation = cell_activation(config, spring.body_a, phase);
        const double target = spring.rest_length * (1.0 - config.contraction_strain * activation);
        add_spring_force(
            spring, target, bodies, result.contraction, result.contraction_energy,
            contraction_balance, contraction_scale
        );
    }
    double junction_balance = 0.0;
    double junction_scale = 0.0;
    if(config.junctions_enabled) {
        for(const auto& spring : junctions) {
            add_spring_force(
                spring, spring.rest_length, bodies, result.adhesion, result.adhesion_energy,
                junction_balance, junction_scale
            );
        }
    }
    result.junction_balance_residual = junction_balance / std::max(junction_scale, kTiny);
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        const auto& nodes = bodies[body_index].surface->get_node_lst();
        for(std::size_t node_index = 0; node_index < nodes.size(); ++node_index) {
            if(!nodes[node_index].is_used()) continue;
            if(bodies[body_index].axial_support[node_index]) {
                const double displacement_x = node_position(nodes[node_index])[0]
                    - bodies[body_index].initial_positions[node_index][0];
                result.support[body_index][node_index][0] = -config.support_stiffness * displacement_x;
                result.support_energy += 0.5 * config.support_stiffness
                    * displacement_x * displacement_x;
            }
            Vector3 total = add(
                add(result.passive[body_index][node_index], result.shape[body_index][node_index]),
                add(
                    result.contraction[body_index][node_index],
                    add(result.adhesion[body_index][node_index], result.support[body_index][node_index])
                )
            );
            for(std::size_t axis = 0; axis < 3; ++axis) {
                if(bodies[body_index].fixed_axes[node_index][axis]) {
                    result.reaction[body_index][node_index][axis] = -total[axis];
                    total[axis] = 0.0;
                }
            }
            result.maximum_free_force = std::max(result.maximum_free_force, norm(total));
            result.total[body_index][node_index] = total;
        }
    }
    return result;
}

double maximum_speed(
    const std::vector<StripBody>& bodies,
    const StripAssembly& assembly
) {
    double maximum = 0.0;
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        const auto areas = nodal_areas(*bodies[body_index].surface);
        for(std::size_t node_index = 0; node_index < areas.size(); ++node_index) {
            maximum = std::max(
                maximum,
                norm(assembly.total[body_index][node_index])
                    / std::max(kStripDampingDensity * areas[node_index], kTiny)
            );
        }
    }
    return maximum;
}

double strip_minimum_edge(const std::vector<StripBody>& bodies) {
    double result = std::numeric_limits<double>::infinity();
    for(const auto& body : bodies) result = std::min(result, minimum_edge_length(*body.surface));
    return result;
}

std::vector<SurfaceVertexForce> additional_forces(
    const StripBody& body,
    const StripAssembly& assembly,
    const std::size_t body_index
) {
    std::vector<Vector3> values(body.surface->get_node_lst().size(), Vector3{});
    for(std::size_t index = 0; index < values.size(); ++index) {
        values[index] = add(
            add(assembly.shape[body_index][index], assembly.contraction[body_index][index]),
            add(
                assembly.adhesion[body_index][index],
                add(assembly.support[body_index][index], assembly.reaction[body_index][index])
            )
        );
    }
    return as_surface_forces(*body.surface, values);
}

std::array<double, 3> body_spans(const StripBody& body) {
    Vector3 lower{
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity()
    };
    Vector3 upper{
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity()
    };
    for(const node& current_node : body.surface->get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 point = node_position(current_node);
        for(std::size_t axis = 0; axis < 3; ++axis) {
            lower[axis] = std::min(lower[axis], point[axis]);
            upper[axis] = std::max(upper[axis], point[axis]);
        }
    }
    return {upper[0] - lower[0], upper[1] - lower[1], upper[2] - lower[2]};
}

double maximum_fixed_displacement_strip(const std::vector<StripBody>& bodies) {
    double result = 0.0;
    for(const auto& body : bodies) {
        for(std::size_t index = 0; index < body.fixed_axes.size(); ++index) {
            const Vector3 displacement = subtract(
                node_position(body.surface->get_node_lst()[index]), body.initial_positions[index]
            );
            for(std::size_t axis = 0; axis < 3; ++axis) {
                if(body.fixed_axes[index][axis]) {
                    result = std::max(result, std::abs(displacement[axis]));
                }
            }
        }
    }
    return result;
}

double strip_x_span(const std::vector<StripBody>& bodies) {
    double minimum = std::numeric_limits<double>::infinity();
    double maximum = -std::numeric_limits<double>::infinity();
    for(const auto& body : bodies) {
        for(const node& current_node : body.surface->get_node_lst()) {
            if(!current_node.is_used()) continue;
            const double x = node_position(current_node)[0];
            minimum = std::min(minimum, x);
            maximum = std::max(maximum, x);
        }
    }
    return maximum - minimum;
}

std::size_t constrained_node_count(const std::vector<StripBody>& bodies) {
    std::size_t result = 0;
    for(const auto& body : bodies) {
        for(const auto& axes : body.fixed_axes) {
            if(axes[0] || axes[1] || axes[2]) ++result;
        }
    }
    return result;
}

std::size_t constrained_axis_count(const std::vector<StripBody>& bodies) {
    std::size_t result = 0;
    for(const auto& body : bodies) {
        for(const auto& axes : body.fixed_axes) {
            for(const bool fixed_axis : axes) result += fixed_axis ? 1U : 0U;
        }
    }
    return result;
}

std::size_t axial_support_count(const std::vector<StripBody>& bodies) {
    std::size_t result = 0;
    for(const auto& body : bodies) {
        for(const bool supported : body.axial_support) result += supported ? 1U : 0U;
    }
    return result;
}

double minimum_adjacent_node_distance(const std::vector<StripBody>& bodies) {
    double result = std::numeric_limits<double>::infinity();
    for(std::size_t pair = 0; pair + 1 < bodies.size(); ++pair) {
        for(const node& first : bodies[pair].surface->get_node_lst()) {
            if(!first.is_used()) continue;
            for(const node& second : bodies[pair + 1].surface->get_node_lst()) {
                if(!second.is_used()) continue;
                result = std::min(result, norm(subtract(node_position(first), node_position(second))));
            }
        }
    }
    return result;
}

void write_faces(
    const std::vector<StripBody>& bodies,
    const unsigned snapshot,
    std::ofstream& stream
) {
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        for(const face& current_face : bodies[body_index].surface->get_face_lst()) {
            if(!current_face.is_used()) continue;
            const auto ids = current_face.get_node_ids();
            stream << snapshot << ',' << body_index << ',' << current_face.get_local_id() << ','
                   << ids[0] << ',' << ids[1] << ',' << ids[2] << '\n';
        }
    }
}

struct SnapshotSummary {
    double end_reaction{};
    double left_reaction_x{};
    double right_reaction_x{};
    double left_external_load_x{};
    double right_external_load_x{};
    double mean_axial_end_load{};
    double strip_span{};
    double maximum_volume_error{};
    double minimum_angle{std::numeric_limits<double>::infinity()};
    double mean_p{};
    double mean_q{};
    double mean_r{};
};

SnapshotSummary write_snapshot(
    std::vector<StripBody>& bodies,
    const StripConfig& config,
    const RunConfig& shape_config,
    const std::vector<MaterialSpring>& contractile,
    const std::vector<MaterialSpring>& junctions,
    const unsigned snapshot,
    const double phase,
    std::ofstream& nodes_stream,
    std::ofstream& state_stream,
    std::ofstream& cell_stream
) {
    const auto assembly = assemble_strip(bodies, config, shape_config, contractile, junctions, phase);
    SnapshotSummary summary;
    double passive_energy_sum = 0.0;
    Vector3 global_force{};
    double global_force_scale = 0.0;
    for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
        const auto areas = nodal_areas(*bodies[body_index].surface);
        const auto spans = body_spans(bodies[body_index]);
        summary.mean_p += spans[0] / static_cast<double>(bodies.size());
        summary.mean_q += spans[1] / static_cast<double>(bodies.size());
        summary.mean_r += spans[2] / static_cast<double>(bodies.size());
        const double volume_error = std::abs(bodies[body_index].surface->get_volume() - kTargetVolume) / kTargetVolume;
        summary.maximum_volume_error = std::max(summary.maximum_volume_error, volume_error);
        summary.minimum_angle = std::min(summary.minimum_angle, minimum_triangle_angle_degrees(*bodies[body_index].surface));
        passive_energy_sum += passive_energy(*bodies[body_index].surface);
        cell_stream << std::setprecision(17)
                    << snapshot << ',' << phase << ',' << activation_value(phase) << ',' << body_index << ','
                    << cell_activation(config, body_index, phase) << ','
                    << spans[0] << ',' << spans[1] << ',' << spans[2] << ','
                    << bodies[body_index].surface->get_area() << ','
                    << bodies[body_index].surface->get_volume() << ',' << volume_error << '\n';
        for(std::size_t node_index = 0; node_index < bodies[body_index].surface->get_node_lst().size(); ++node_index) {
            const node& current_node = bodies[body_index].surface->get_node_lst()[node_index];
            if(!current_node.is_used()) continue;
            const Vector3 position = node_position(current_node);
            const Vector3 physical_total = add(
                add(assembly.passive[body_index][node_index], assembly.shape[body_index][node_index]),
                add(
                    assembly.contraction[body_index][node_index],
                    add(assembly.adhesion[body_index][node_index], assembly.support[body_index][node_index])
                )
            );
            const Vector3 total_with_reaction = add(
                physical_total, assembly.reaction[body_index][node_index]
            );
            global_force = add(global_force, total_with_reaction);
            global_force_scale += norm(total_with_reaction);
            if(body_index == 0) {
                summary.left_reaction_x += assembly.reaction[body_index][node_index][0];
                summary.left_external_load_x += assembly.reaction[body_index][node_index][0]
                    + assembly.support[body_index][node_index][0];
            }
            if(body_index + 1 == bodies.size()) {
                summary.right_reaction_x += assembly.reaction[body_index][node_index][0];
                summary.right_external_load_x += assembly.reaction[body_index][node_index][0]
                    + assembly.support[body_index][node_index][0];
            }
            const auto& fixed_axes = bodies[body_index].fixed_axes[node_index];
            const bool any_fixed = fixed_axes[0] || fixed_axes[1] || fixed_axes[2];
            nodes_stream << std::setprecision(17)
                << snapshot << ',' << phase << ',' << activation_value(phase) << ','
                << body_index << ',' << node_index << ',' << current_node.get_persistent_id() << ','
                << position[0] << ',' << position[1] << ',' << position[2] << ','
                << areas[node_index] << ',' << current_node.get_curvature() << ','
                << bodies[body_index].surface->get_pressure() << ','
                << (any_fixed ? 1 : 0) << ','
                << (fixed_axes[0] ? 1 : 0) << ','
                << (fixed_axes[1] ? 1 : 0) << ','
                << (fixed_axes[2] ? 1 : 0) << ','
                << assembly.passive[body_index][node_index][0] << ','
                << assembly.passive[body_index][node_index][1] << ','
                << assembly.passive[body_index][node_index][2] << ','
                << assembly.shape[body_index][node_index][0] << ','
                << assembly.shape[body_index][node_index][1] << ','
                << assembly.shape[body_index][node_index][2] << ','
                << assembly.contraction[body_index][node_index][0] << ','
                << assembly.contraction[body_index][node_index][1] << ','
                << assembly.contraction[body_index][node_index][2] << ','
                << assembly.adhesion[body_index][node_index][0] << ','
                << assembly.adhesion[body_index][node_index][1] << ','
                << assembly.adhesion[body_index][node_index][2] << ','
                << assembly.support[body_index][node_index][0] << ','
                << assembly.support[body_index][node_index][1] << ','
                << assembly.support[body_index][node_index][2] << ','
                << assembly.reaction[body_index][node_index][0] << ','
                << assembly.reaction[body_index][node_index][1] << ','
                << assembly.reaction[body_index][node_index][2] << ','
                << total_with_reaction[0] << ',' << total_with_reaction[1] << ',' << total_with_reaction[2] << ','
                << norm(assembly.shape[body_index][node_index]) / std::max(areas[node_index], kTiny) << ','
                << norm(assembly.contraction[body_index][node_index]) / std::max(areas[node_index], kTiny) << ','
                << norm(assembly.adhesion[body_index][node_index]) / std::max(areas[node_index], kTiny) << ','
                << norm(assembly.support[body_index][node_index]) / std::max(areas[node_index], kTiny) << ','
                << norm(total_with_reaction) / std::max(areas[node_index], kTiny) << '\n';
        }
    }
    summary.end_reaction = 0.5 * (std::abs(summary.left_reaction_x) + std::abs(summary.right_reaction_x));
    summary.mean_axial_end_load = 0.5 * (
        std::abs(summary.left_external_load_x) + std::abs(summary.right_external_load_x)
    );
    summary.strip_span = strip_x_span(bodies);
    const double global_balance = norm(global_force) / std::max(global_force_scale, kTiny);
    state_stream << std::setprecision(17)
        << snapshot << ',' << phase << ',' << activation_value(phase) << ','
        << summary.end_reaction << ',' << summary.left_reaction_x << ',' << summary.right_reaction_x << ','
        << config.boundary_mode << ',' << config.support_stiffness << ','
        << summary.left_external_load_x << ',' << summary.right_external_load_x << ','
        << summary.mean_axial_end_load << ',' << summary.strip_span << ','
        << summary.mean_p << ',' << summary.mean_q << ',' << summary.mean_r << ','
        << summary.maximum_volume_error << ',' << summary.minimum_angle << ','
        << maximum_fixed_displacement_strip(bodies) << ','
        << minimum_adjacent_node_distance(bodies) << ','
        << assembly.maximum_free_force << ',' << global_balance << ','
        << assembly.junction_balance_residual << ','
        << passive_energy_sum << ',' << assembly.contraction_energy << ',' << assembly.adhesion_energy << ','
        << assembly.support_energy << '\n';
    for(auto& body : bodies) reset_forces(*body.surface);
    return summary;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const StripConfig config = parse_strip_config(argc, argv);
        const std::filesystem::path output_directory = std::filesystem::absolute(argv[1]);
        if(std::filesystem::exists(output_directory)) throw std::runtime_error("create-only strip output already exists");
        std::filesystem::create_directories(output_directory);
        omp_set_num_threads(1);
        const auto started = std::chrono::steady_clock::now();
        const mesh base = load_frozen_mesh(config.input_nodes, config.input_faces);
        const auto left_cap = cap_nodes(base, false);
        const auto right_cap = cap_nodes(base, true);
        const auto cap_pairs = match_caps(base, right_cap, left_cap);
        if(cap_pairs.size() != 7) throw std::runtime_error("frozen end cap must contain exactly seven material pairs");

        double minimum_x = std::numeric_limits<double>::infinity();
        double maximum_x = -std::numeric_limits<double>::infinity();
        for(std::size_t index = 0; index < base.node_pos_lst.size() / 3; ++index) {
            minimum_x = std::min(minimum_x, base.node_pos_lst[3 * index]);
            maximum_x = std::max(maximum_x, base.node_pos_lst[3 * index]);
        }
        const double spacing = maximum_x - minimum_x + kInterfaceGap;
        const double local_center = 0.5 * (minimum_x + maximum_x);
        const mesh sphere_reference = make_icosphere(2, 0.0, 0.0);
        const auto reference_measure = measure_mesh(sphere_reference);
        const double target_isoperimetric_ratio = std::pow(reference_measure.area, 3)
            / std::pow(std::abs(reference_measure.signed_volume), 2);

        std::vector<StripBody> bodies;
        for(std::size_t body_index = 0; body_index < kStripCellCount; ++body_index) {
            mesh translated = base;
            const double offset = (static_cast<double>(body_index) - 2.0) * spacing - local_center;
            for(std::size_t node_index = 0; node_index < translated.node_pos_lst.size() / 3; ++node_index) {
                translated.node_pos_lst[3 * node_index] += offset;
            }
            StripBody body;
            body.surface = std::make_shared<cell>(translated, static_cast<unsigned>(body_index), make_myocardium_type(target_isoperimetric_ratio));
            body.surface->initialize_cell_properties();
            body.surface->update_centroid();
            body.fixed_axes.assign(body.surface->get_node_lst().size(), {false, false, false});
            body.axial_support.assign(body.surface->get_node_lst().size(), false);
            for(const node& current_node : body.surface->get_node_lst()) {
                body.initial_positions.push_back(node_position(current_node));
            }
            bodies.push_back(std::move(body));
        }
        if(config.boundary_mode == "ISOMETRIC") {
            for(const std::size_t node_id : left_cap) bodies.front().fixed_axes[node_id] = {true, true, true};
            for(const std::size_t node_id : right_cap) bodies.back().fixed_axes[node_id] = {true, true, true};
        } else if(config.boundary_mode == "COMPLIANT") {
            for(const std::size_t node_id : left_cap) {
                bodies.front().fixed_axes[node_id] = {false, true, true};
                bodies.front().axial_support[node_id] = true;
            }
            for(const std::size_t node_id : right_cap) {
                bodies.back().fixed_axes[node_id] = {false, true, true};
                bodies.back().axial_support[node_id] = true;
            }
        } else {
            for(const std::size_t node_id : left_cap) bodies.front().fixed_axes[node_id] = {true, true, true};
            for(const std::size_t node_id : right_cap) bodies.back().fixed_axes[node_id] = {false, true, true};
        }

        std::vector<MaterialSpring> contractile;
        std::vector<MaterialSpring> junctions;
        for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
            for(const auto& pair : cap_pairs) {
                const Vector3 right = node_position(bodies[body_index].surface->get_node_lst()[pair.first]);
                const Vector3 left = node_position(bodies[body_index].surface->get_node_lst()[pair.second]);
                contractile.push_back({
                    body_index, pair.first, body_index, pair.second,
                    norm(subtract(left, right)), kContractionStiffness, -1
                });
            }
        }
        for(std::size_t interface_id = 0; interface_id + 1 < bodies.size(); ++interface_id) {
            for(const auto& pair : cap_pairs) {
                const Vector3 right = node_position(bodies[interface_id].surface->get_node_lst()[pair.first]);
                const Vector3 left = node_position(bodies[interface_id + 1].surface->get_node_lst()[pair.second]);
                junctions.push_back({
                    interface_id, pair.first, interface_id + 1, pair.second,
                    norm(subtract(left, right)), kJunctionStiffness, static_cast<int>(interface_id)
                });
            }
        }

        RunConfig shape_config = parse_config("FULL", 320, config.requested_step, kShapeStress);
        std::ofstream nodes_stream(output_directory / "nodes.csv");
        std::ofstream faces_stream(output_directory / "faces.csv");
        std::ofstream state_stream(output_directory / "state_metrics.csv");
        std::ofstream cell_stream(output_directory / "cell_metrics.csv");
        std::ofstream audit_stream(output_directory / "step_audits.csv");
        nodes_stream << "snapshot_index,phase,activation,cell_id,node_index,persistent_id,x,y,z,nodal_area,curvature,internal_pressure,fixed,fixed_x,fixed_y,fixed_z,passive_fx,passive_fy,passive_fz,shape_fx,shape_fy,shape_fz,contraction_fx,contraction_fy,contraction_fz,adhesion_fx,adhesion_fy,adhesion_fz,support_fx,support_fy,support_fz,reaction_fx,reaction_fy,reaction_fz,total_fx,total_fy,total_fz,shape_traction,contraction_traction,adhesion_traction,support_traction,total_traction\n";
        faces_stream << "snapshot_index,cell_id,face_local_id,n1,n2,n3\n";
        state_stream << "snapshot_index,phase,activation,end_reaction,left_reaction_x,right_reaction_x,boundary_mode,support_stiffness,left_external_load_x,right_external_load_x,mean_axial_end_load,strip_x_span,mean_p_span,mean_q_span,mean_r_span,max_volume_relative_error,min_triangle_angle_deg,max_fixed_displacement,min_adjacent_node_distance,max_free_force,global_force_balance_residual,junction_balance_residual,passive_energy,contraction_energy,adhesion_energy,support_energy\n";
        cell_stream << "snapshot_index,phase,activation,cell_id,cell_activation,p_span,q_span,r_span,area,volume,volume_relative_error\n";
        audit_stream << "requested_step,substep,phase,activation,accepted_step,max_free_force,max_volume_relative_error,min_triangle_angle_deg,max_fixed_displacement,max_work_relative_residual\n";

        unsigned requested_step_index = 0;
        std::uint64_t substep_index = 0;
        double maximum_work_residual = 0.0;
        double minimum_accepted_step = std::numeric_limits<double>::infinity();
        double maximum_volume_error = 0.0;
        double minimum_angle = std::numeric_limits<double>::infinity();
        double maximum_fixed_displacement = 0.0;

        auto advance_requested = [&](const double phase) {
            ++requested_step_index;
            double remaining = config.requested_step;
            unsigned guard = 0;
            while(remaining > config.requested_step * 1.0e-12) {
                if(++guard > 10000) throw std::runtime_error("strip adaptive substep guard exceeded");
                auto assembly = assemble_strip(bodies, config, shape_config, contractile, junctions, phase);
                const double speed = maximum_speed(bodies, assembly);
                const double motion_limit = speed > kTiny
                    ? kStripMotionFraction * strip_minimum_edge(bodies) / speed
                    : remaining;
                const double accepted = std::min(remaining, motion_limit);
                if(!(accepted > 0.0) || !std::isfinite(accepted)) throw std::runtime_error("invalid strip substep");
                minimum_accepted_step = std::min(minimum_accepted_step, accepted);
                double current_work_residual = 0.0;
                for(std::size_t body_index = 0; body_index < bodies.size(); ++body_index) {
                    const auto audit = prl::cell_engine::advance_surface_overdamped(
                        *bodies[body_index].surface,
                        bodies[body_index].surface->get_mesh_revision(),
                        accepted,
                        SurfaceDampingLaw{SurfaceDampingMeasure::barycentric_dual_area, kStripDampingDensity},
                        additional_forces(bodies[body_index], assembly, body_index)
                    );
                    bodies[body_index].surface->update_centroid();
                    const double relative = audit.work_dissipation_residual
                        / std::max({std::abs(audit.total_force_work), std::abs(audit.viscous_dissipation), kTiny});
                    current_work_residual = std::max(current_work_residual, relative);
                }
                maximum_work_residual = std::max(maximum_work_residual, current_work_residual);
                double current_volume_error = 0.0;
                double current_angle = std::numeric_limits<double>::infinity();
                for(auto& body : bodies) {
                    static_cast<void>(prl::cell_engine::refresh_surface_geometry(*body.surface, body.surface->get_mesh_revision()));
                    current_volume_error = std::max(
                        current_volume_error,
                        std::abs(body.surface->get_volume() - kTargetVolume) / kTargetVolume
                    );
                    current_angle = std::min(current_angle, minimum_triangle_angle_degrees(*body.surface));
                }
                const double fixed_displacement = maximum_fixed_displacement_strip(bodies);
                maximum_volume_error = std::max(maximum_volume_error, current_volume_error);
                minimum_angle = std::min(minimum_angle, current_angle);
                maximum_fixed_displacement = std::max(maximum_fixed_displacement, fixed_displacement);
                ++substep_index;
                audit_stream << std::setprecision(17)
                    << requested_step_index << ',' << substep_index << ',' << phase << ','
                    << activation_value(phase) << ',' << accepted << ',' << assembly.maximum_free_force << ','
                    << current_volume_error << ',' << current_angle << ',' << fixed_displacement << ','
                    << current_work_residual << '\n';
                if(current_volume_error > 0.05) throw std::runtime_error("strip volume error exceeded five-percent safety stop");
                if(current_angle < 8.0) throw std::runtime_error("strip minimum angle crossed eight-degree safety stop");
                remaining -= accepted;
            }
        };

        for(unsigned step = 0; step < config.settle_steps; ++step) advance_requested(0.0);
        unsigned snapshot = 0;
        write_faces(bodies, snapshot, faces_stream);
        write_snapshot(bodies, config, shape_config, contractile, junctions, snapshot++, 0.0, nodes_stream, state_stream, cell_stream);
        for(unsigned segment = 0; segment < 8; ++segment) {
            for(unsigned local_step = 1; local_step <= config.ramp_steps_per_segment; ++local_step) {
                const double phase = (
                    static_cast<double>(segment)
                    + static_cast<double>(local_step) / static_cast<double>(config.ramp_steps_per_segment)
                ) / 8.0;
                advance_requested(phase);
            }
            const double phase = static_cast<double>(segment + 1) / 8.0;
            for(unsigned hold_step = 0; hold_step < config.hold_steps_per_segment; ++hold_step) {
                advance_requested(phase);
            }
            write_faces(bodies, snapshot, faces_stream);
            write_snapshot(bodies, config, shape_config, contractile, junctions, snapshot++, phase, nodes_stream, state_stream, cell_stream);
        }

        std::ofstream metrics(output_directory / "kernel_metrics.json");
        const std::string stage_name = config.boundary_mode_explicit
            ? "Z1-MYO-STRIP-LOAD-BC-A"
            : "Z1-MYO-STRIP-L5-A";
        metrics << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"stage\": \"" << stage_name << "\",\n"
            << "  \"raw_execution_status\": \"completed\",\n"
            << "  \"condition\": \"" << config.condition << "\",\n"
            << "  \"boundary_mode\": \"" << config.boundary_mode << "\",\n"
            << "  \"support_stiffness\": " << config.support_stiffness << ",\n"
            << "  \"kernel\": \"PRL-controlled SimuCell3D\",\n"
            << "  \"coordinate_semantics\": \"algorithmic_activation_phase_not_physiological_time\",\n"
            << "  \"cell_count\": 5,\n"
            << "  \"nodes_per_cell\": 162,\n"
            << "  \"faces_per_cell\": 320,\n"
            << "  \"snapshot_count\": 9,\n"
            << "  \"requested_step_count\": " << requested_step_index << ",\n"
            << "  \"substep_count\": " << substep_index << ",\n"
            << "  \"requested_step\": " << config.requested_step << ",\n"
            << "  \"settle_steps\": " << config.settle_steps << ",\n"
            << "  \"ramp_steps_per_segment\": " << config.ramp_steps_per_segment << ",\n"
            << "  \"hold_steps_per_segment\": " << config.hold_steps_per_segment << ",\n"
            << "  \"minimum_accepted_step\": " << minimum_accepted_step << ",\n"
            << "  \"shape_stress\": " << kShapeStress << ",\n"
            << "  \"contraction_strain\": " << config.contraction_strain << ",\n"
            << "  \"contraction_stiffness\": " << kContractionStiffness << ",\n"
            << "  \"junction_stiffness\": " << kJunctionStiffness << ",\n"
            << "  \"surface_damping_density\": " << kStripDampingDensity << ",\n"
            << "  \"junctions_enabled\": " << (config.junctions_enabled ? "true" : "false") << ",\n"
            << "  \"junction_count\": " << (config.junctions_enabled ? junctions.size() : 0) << ",\n"
            << "  \"junction_links_per_interface\": " << cap_pairs.size() << ",\n"
            << "  \"contractile_unit_count\": " << contractile.size() << ",\n"
            << "  \"fixed_node_count\": " << constrained_node_count(bodies) << ",\n"
            << "  \"fixed_axis_count\": " << constrained_axis_count(bodies) << ",\n"
            << "  \"axial_support_count\": " << axial_support_count(bodies) << ",\n"
            << "  \"reference_edge_shape_terms\": 0,\n"
            << "  \"reference_face_metric_terms\": 0,\n"
            << "  \"target_geometry_used\": false,\n"
            << "  \"bending_modulus\": 0.0,\n"
            << "  \"dynamic_remeshing\": false,\n"
            << "  \"maximum_volume_relative_error\": " << maximum_volume_error << ",\n"
            << "  \"minimum_triangle_angle_deg\": " << minimum_angle << ",\n"
            << "  \"maximum_fixed_displacement\": " << maximum_fixed_displacement << ",\n"
            << "  \"maximum_work_relative_residual\": " << maximum_work_residual << ",\n"
            << "  \"elapsed_seconds\": "
            << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << "\n"
            << "}\n";
        std::cout << stage_name << " raw condition complete\ncondition=" << config.condition
                  << "\nboundary=" << config.boundary_mode
                  << "\nsteps=" << requested_step_index << "\nsubsteps=" << substep_index << '\n';
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "Z1-MYO-STRIP-L5-A failed: " << error.what() << '\n';
        return 2;
    }
}
