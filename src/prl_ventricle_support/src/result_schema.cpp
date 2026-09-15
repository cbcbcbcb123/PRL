#include "prl/ventricle_support/result_schema.hpp"

#include <stdexcept>

namespace prl::ventricle_support {

ResultSchema result_schema(const ResultTable table) {
    switch(table) {
        case ResultTable::contact_nodes_v1:
            return {
                "prl.contact_nodes.v1",
                "cell,node,x0,y0,z0,x,y,z,fx,fy,fz,area,curvature,pressure,coupled",
                15,
            };
        case ResultTable::long_doublet_nodes_v1:
            return {
                "prl.long_doublet.nodes.v1",
                "snapshot,step,coordinate,cell,node,x,y,z,fx,fy,fz,cfx,cfy,cfz,sfx,sfy,sfz,rfx,rfy,rfz,area,curvature,pressure,fixed,x0,y0,z0",
                27,
            };
        case ResultTable::long_doublet_faces_v1:
            return {"prl.long_doublet.faces.v1", "cell,face,a,b,c", 5};
        case ResultTable::long_doublet_states_v1:
            return {
                "prl.long_doublet.states.v1",
                "snapshot,step,coordinate,max_free_force,max_volume_error,min_angle,max_fixed_displacement,contact_energy,contact_support_area,passive_energy",
                10,
            };
        case ResultTable::long_doublet_cells_v1:
            return {
                "prl.long_doublet.cells.v1",
                "snapshot,cell,volume,target_volume,length,width,thickness,pressure",
                8,
            };
        case ResultTable::long_doublet_step_audits_v1:
            return {
                "prl.long_doublet.step_audits.v1",
                "step,coordinate,max_free_force,max_volume_error,min_angle,max_fixed_displacement,work_residual,shape_work,dissipation,contact_energy",
                10,
            };
        case ResultTable::long_doublet_separation_v1:
            return {
                "prl.long_doublet.separation.v1",
                "step,coordinate,intercell_distance,nonincident_distance,min_height,increment",
                6,
            };
    }
    throw std::invalid_argument("unknown PRL result table");
}

std::string csv_escape(const std::string_view value) {
    bool requires_quotes = false;
    for(const char character : value) {
        requires_quotes = requires_quotes
            || character == ','
            || character == '"'
            || character == '\n'
            || character == '\r';
    }
    if(!requires_quotes) return std::string(value);

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

}  // namespace prl::ventricle_support
