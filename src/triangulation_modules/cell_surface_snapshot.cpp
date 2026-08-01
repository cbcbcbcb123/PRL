#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "face.hpp"
#include "node.hpp"

#include <cstdint>
#include <unordered_map>

namespace prl::cell_engine {

core::SurfaceMeshSnapshot capture_surface_snapshot(const ::cell& source) {
    core::SurfaceMeshSnapshot snapshot;
    snapshot.cell_id = source.get_id();
    snapshot.revision = source.get_mesh_revision();
    snapshot.vertices.reserve(source.get_nb_of_nodes());
    snapshot.faces.reserve(source.get_nb_of_faces());

    std::unordered_map<unsigned, std::uint32_t> compact_vertex_index;
    compact_vertex_index.reserve(source.get_nb_of_nodes());
    for(const node& current_node : source.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const auto compact_index = static_cast<std::uint32_t>(snapshot.vertices.size());
        compact_vertex_index.emplace(current_node.get_local_id(), compact_index);
        snapshot.vertices.push_back({
            current_node.get_persistent_id(),
            {
                current_node.pos().dx(),
                current_node.pos().dy(),
                current_node.pos().dz(),
            },
        });
    }

    for(const face& current_face : source.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto node_ids = current_face.get_node_ids();
        snapshot.faces.push_back({{
            compact_vertex_index.at(node_ids[0]),
            compact_vertex_index.at(node_ids[1]),
            compact_vertex_index.at(node_ids[2]),
        }});
    }
    return snapshot;
}

} // namespace prl::cell_engine
