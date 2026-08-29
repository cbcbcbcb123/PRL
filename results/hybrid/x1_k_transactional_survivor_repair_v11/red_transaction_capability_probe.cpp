#include "prl_cell_engine/remesh_contract.hpp"
void probe(prl::core::RemeshEventSink& sink,
           const prl::core::RemeshEvent& event,
           const prl::core::SurfaceMeshSnapshot& before,
           const prl::core::SurfaceMeshSnapshot& after) {
    (void)sink.prepare_remesh(event, before, after);
}
