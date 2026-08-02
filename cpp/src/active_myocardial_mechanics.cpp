#include "prl/core/active_myocardial_mechanics.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace prl::core {
namespace {

using Vector3 = std::array<double, 3>;

constexpr double geometric_epsilon = 1.0e-14;
constexpr double barycentric_tolerance = 1.0e-12;

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 scale(const Vector3& value, const double factor) noexcept {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

double dot(const Vector3& left, const Vector3& right) noexcept {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

Vector3 cross(const Vector3& left, const Vector3& right) noexcept {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double norm(const Vector3& value) noexcept {
    return std::sqrt(dot(value, value));
}

bool finite_vector(const Vector3& value) noexcept {
    return std::all_of(value.begin(), value.end(), [](const double component) {
        return std::isfinite(component);
    });
}

Vector3 normalized(const Vector3& value, const char* const message) {
    const double length = norm(value);
    if(!std::isfinite(length) || length <= geometric_epsilon) {
        throw std::invalid_argument(message);
    }
    return scale(value, 1.0 / length);
}

struct ResolvedPoint {
    const SurfaceMaterialPoint* material_point{};
    Vector3 position{};
    std::array<std::size_t, 3> vertex_indices{};
};

std::unordered_map<VertexId, std::size_t> vertex_indices(
    const SurfaceMeshSnapshot& mesh
) {
    std::unordered_map<VertexId, std::size_t> result;
    result.reserve(mesh.vertices.size());
    for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
        const auto& vertex = mesh.vertices[index];
        if(!finite_vector(vertex.position)) {
            throw std::invalid_argument("active mesh contains a non-finite vertex");
        }
        if(!result.emplace(vertex.persistent_id, index).second) {
            throw std::invalid_argument("active mesh vertex IDs must be unique");
        }
    }
    return result;
}

std::unordered_map<MaterialPointId, const SurfaceMaterialPoint*> material_points(
    const MyocardialCellMaterialState& material
) {
    std::unordered_map<MaterialPointId, const SurfaceMaterialPoint*> result;
    result.reserve(material.points.size());
    for(const auto& point : material.points) {
        if(!result.emplace(point.material.material_point_id, &point).second) {
            throw std::invalid_argument("active material-point IDs must be unique");
        }
    }
    return result;
}

ResolvedPoint resolve_point(
    const SurfaceMaterialPoint& point,
    const SurfaceMeshSnapshot& mesh,
    const std::unordered_map<VertexId, std::size_t>& vertex_by_id
) {
    ResolvedPoint result;
    result.material_point = &point;
    double barycentric_sum = 0.0;
    for(std::size_t corner = 0; corner < 3; ++corner) {
        const double weight = point.barycentric[corner];
        if(!std::isfinite(weight)
           || weight < -barycentric_tolerance
           || weight > 1.0 + barycentric_tolerance) {
            throw std::invalid_argument("active material point has invalid barycentric coordinates");
        }
        barycentric_sum += weight;
        const auto vertex = vertex_by_id.find(point.host_vertex_ids[corner]);
        if(vertex == vertex_by_id.end()) {
            throw std::invalid_argument("active material point references a missing vertex");
        }
        result.vertex_indices[corner] = vertex->second;
        result.position = add(
            result.position,
            scale(mesh.vertices[vertex->second].position, weight)
        );
    }
    if(std::abs(barycentric_sum - 1.0) > barycentric_tolerance) {
        throw std::invalid_argument("active material-point barycentric weights must sum to one");
    }
    return result;
}

const SurfaceMaterialPoint& point_by_id(
    const std::unordered_map<MaterialPointId, const SurfaceMaterialPoint*>& points,
    const MaterialPointId id
) {
    const auto point = points.find(id);
    if(point == points.end()) {
        throw std::invalid_argument("active contraction unit references a missing material point");
    }
    return *point->second;
}

void validate_unit_parameters(const ActiveContractionUnit& unit) {
    if(!std::isfinite(unit.reference_length) || unit.reference_length <= geometric_epsilon) {
        throw std::invalid_argument("active reference length must be finite and positive");
    }
    if(!std::isfinite(unit.stiffness) || unit.stiffness <= 0.0) {
        throw std::invalid_argument("active stiffness must be finite and positive");
    }
    if(!std::isfinite(unit.minimum_axis_fiber_alignment)
       || unit.minimum_axis_fiber_alignment < 0.0
       || unit.minimum_axis_fiber_alignment > 1.0) {
        throw std::invalid_argument("active axis-fiber alignment threshold must lie in [0,1]");
    }
    if(unit.minus_material_point_id == unit.plus_material_point_id) {
        throw std::invalid_argument("active contraction anchors must be distinct");
    }
}

ActivationSample activation_from(const SurfaceMaterialPoint& point) {
    if(point.material.active_state.size() != 2) {
        throw std::invalid_argument(
            "active controller state must contain [activation, activation_rate]"
        );
    }
    const double activation = point.material.active_state[0];
    const double rate = point.material.active_state[1];
    if(!std::isfinite(activation) || activation < 0.0 || activation > 0.2) {
        throw std::invalid_argument("activation must remain inside the frozen [0,0.2] bounds");
    }
    if(!std::isfinite(rate)) {
        throw std::invalid_argument("activation rate must be finite");
    }
    return {activation, rate};
}

double axis_fiber_alignment(const Vector3& axis, const SurfaceMaterialPoint& controller) {
    const auto fiber = normalized(
        controller.material.fiber_direction,
        "active controller fiber must be nonzero"
    );
    return std::abs(dot(axis, fiber));
}

} // namespace

ActivationSample c1_activation_protocol(
    const double time,
    const double delay,
    const double alpha_peak
) {
    if(!std::isfinite(time) || !std::isfinite(delay)) {
        throw std::invalid_argument("activation time and delay must be finite");
    }
    if(!std::isfinite(alpha_peak) || alpha_peak < 0.0 || alpha_peak > 0.2) {
        throw std::invalid_argument("activation peak must lie in [0,0.2]");
    }
    const double shifted_time = time - delay;
    double envelope = 0.0;
    double envelope_rate = 0.0;
    const double pi = std::acos(-1.0);
    if(shifted_time >= 1.0 && shifted_time < 2.0) {
        const double phase = pi * (shifted_time - 1.0);
        envelope = 0.5 * (1.0 - std::cos(phase));
        envelope_rate = 0.5 * pi * std::sin(phase);
    } else if(shifted_time >= 2.0 && shifted_time < 3.0) {
        envelope = 1.0;
    } else if(shifted_time >= 3.0 && shifted_time < 4.0) {
        const double phase = pi * (shifted_time - 3.0);
        envelope = 0.5 * (1.0 + std::cos(phase));
        envelope_rate = -0.5 * pi * std::sin(phase);
    }
    return {alpha_peak * envelope, alpha_peak * envelope_rate};
}

ActiveContractionUnit build_active_contraction_unit(
    const SurfaceMeshSnapshot& reference_mesh,
    const MyocardialCellMaterialState& reference_material,
    const ActiveContractionUnitId contraction_unit_id,
    const MaterialPointId minus_material_point_id,
    const MaterialPointId plus_material_point_id,
    const MaterialPointId activation_material_point_id,
    const double stiffness,
    const double minimum_axis_fiber_alignment
) {
    if(reference_mesh.cell_id != reference_material.cell_id
       || reference_mesh.revision != reference_material.revision) {
        throw std::invalid_argument("active reference mesh and material state must match");
    }
    const auto vertex_by_id = vertex_indices(reference_mesh);
    const auto points = material_points(reference_material);
    const auto minus = resolve_point(
        point_by_id(points, minus_material_point_id),
        reference_mesh,
        vertex_by_id
    );
    const auto plus = resolve_point(
        point_by_id(points, plus_material_point_id),
        reference_mesh,
        vertex_by_id
    );
    const auto& controller = point_by_id(points, activation_material_point_id);
    const auto difference = subtract(plus.position, minus.position);
    const auto axis = normalized(difference, "active reference anchor length must be positive");
    ActiveContractionUnit result{
        contraction_unit_id,
        minus_material_point_id,
        plus_material_point_id,
        activation_material_point_id,
        norm(difference),
        stiffness,
        minimum_axis_fiber_alignment,
    };
    validate_unit_parameters(result);
    if(axis_fiber_alignment(axis, controller) < minimum_axis_fiber_alignment) {
        throw std::invalid_argument("active reference axis is not aligned with its material fiber");
    }
    return result;
}

ActiveContractionEvaluation evaluate_active_contraction(
    const SurfaceMeshSnapshot& mesh,
    const MyocardialCellMaterialState& material,
    const std::vector<ActiveContractionUnit>& units
) {
    if(mesh.cell_id != material.cell_id || mesh.revision != material.revision) {
        throw std::invalid_argument("active mesh and material state must have equal cell/revision");
    }
    if(units.empty()) {
        throw std::invalid_argument("active evaluation requires at least one contraction unit");
    }
    const auto vertex_by_id = vertex_indices(mesh);
    const auto points = material_points(material);
    ActiveContractionEvaluation result;
    result.cell_id = mesh.cell_id;
    result.revision = mesh.revision;
    result.unit_states.reserve(units.size());
    result.vertex_forces.reserve(mesh.vertices.size());
    for(const auto& vertex : mesh.vertices) {
        result.vertex_forces.push_back({vertex.persistent_id, {0.0, 0.0, 0.0}});
    }

    std::unordered_set<ActiveContractionUnitId> unit_ids;
    unit_ids.reserve(units.size());
    double total_energy = 0.0;
    double total_input_power = 0.0;
    double minimum_alignment = 1.0;
    double maximum_activation = 0.0;
    for(const auto& unit : units) {
        validate_unit_parameters(unit);
        if(!unit_ids.emplace(unit.contraction_unit_id).second) {
            throw std::invalid_argument("active contraction-unit IDs must be unique");
        }
        const auto minus = resolve_point(
            point_by_id(points, unit.minus_material_point_id),
            mesh,
            vertex_by_id
        );
        const auto plus = resolve_point(
            point_by_id(points, unit.plus_material_point_id),
            mesh,
            vertex_by_id
        );
        const auto& controller = point_by_id(points, unit.activation_material_point_id);
        const auto activation = activation_from(controller);
        const auto difference = subtract(plus.position, minus.position);
        const double length = norm(difference);
        const auto axis = normalized(difference, "active anchor length became nonpositive");
        const double alignment = axis_fiber_alignment(axis, controller);
        if(alignment < unit.minimum_axis_fiber_alignment) {
            throw std::runtime_error("active anchor axis is not aligned with its material fiber");
        }

        const double preferred_length = unit.reference_length * (1.0 - activation.activation);
        const double preferred_length_rate = -unit.reference_length * activation.activation_rate;
        const double mismatch = length - preferred_length;
        const double energy = 0.5 * unit.stiffness * mismatch * mismatch;
        const double input_power = -unit.stiffness * mismatch * preferred_length_rate;
        const double force_magnitude = unit.stiffness * mismatch;
        const auto minus_force = scale(axis, force_magnitude);
        const auto plus_force = scale(axis, -force_magnitude);
        for(std::size_t corner = 0; corner < 3; ++corner) {
            auto& force = result.vertex_forces[minus.vertex_indices[corner]].force;
            force = add(force, scale(minus_force, minus.material_point->barycentric[corner]));
        }
        for(std::size_t corner = 0; corner < 3; ++corner) {
            auto& force = result.vertex_forces[plus.vertex_indices[corner]].force;
            force = add(force, scale(plus_force, plus.material_point->barycentric[corner]));
        }
        result.unit_states.push_back({
            unit.contraction_unit_id,
            length,
            axis,
            preferred_length,
            preferred_length_rate,
            activation.activation,
            activation.activation_rate,
            energy,
            input_power,
            alignment,
        });
        total_energy += energy;
        total_input_power += input_power;
        minimum_alignment = std::min(minimum_alignment, alignment);
        maximum_activation = std::max(maximum_activation, activation.activation);
    }

    Vector3 net_force{};
    Vector3 net_moment{};
    for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
        const auto& force = result.vertex_forces[index].force;
        net_force = add(net_force, force);
        net_moment = add(net_moment, cross(mesh.vertices[index].position, force));
    }
    result.audit = {
        units.size(),
        total_energy,
        total_input_power,
        norm(net_force),
        norm(net_moment),
        minimum_alignment,
        maximum_activation,
    };
    return result;
}

} // namespace prl::core
