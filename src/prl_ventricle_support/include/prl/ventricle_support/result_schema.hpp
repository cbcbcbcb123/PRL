#pragma once

#include <cstddef>
#include <string>
#include <string_view>

namespace prl::ventricle_support {

enum class ResultTable {
    contact_nodes_v1,
    long_doublet_nodes_v1,
    long_doublet_faces_v1,
    long_doublet_states_v1,
    long_doublet_cells_v1,
    long_doublet_step_audits_v1,
    long_doublet_separation_v1,
};

struct ResultSchema {
    std::string_view identifier;
    std::string_view header;
    std::size_t column_count;
};

ResultSchema result_schema(ResultTable table);
std::string csv_escape(std::string_view value);

}  // namespace prl::ventricle_support
