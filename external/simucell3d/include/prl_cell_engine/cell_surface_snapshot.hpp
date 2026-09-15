#pragma once

#include "prl_cell_engine/remesh_contract.hpp"

class cell;

namespace prl::cell_engine {

/**
 * Copy the current used cell surface into stable PRL value types.
 *
 * The same adapter is used for initial material registration and remesh event
 * emission, preventing two subtly different snapshot representations.
 */
[[nodiscard]] core::SurfaceMeshSnapshot capture_surface_snapshot(const ::cell& source);

} // namespace prl::cell_engine
