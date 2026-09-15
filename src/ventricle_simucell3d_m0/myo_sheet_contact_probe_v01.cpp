// Reuse the existing adapter helpers and the unique linked core; do not copy a kernel.
#define main preserved_migration_entrypoint
#include "ventricle_simucell3d_m0.cpp"
#undef main

int main(int argc, char** argv) {
    try {
        if(argc != 4) throw std::runtime_error("usage: probe mesh_input output_directory type_id");
        omp_set_num_threads(1);
        std::ifstream input(argv[1]);
        if(!input) throw std::runtime_error("input missing");
        unsigned count; input >> count;
        if(count != 2) throw std::runtime_error("two cells required");
        std::vector<Body> bodies;
        const short type_id = static_cast<short>(std::stoi(argv[3]));
        for(unsigned id=0; id<count; ++id) {
            unsigned nv,nf; input >> nv >> nf;
            mesh geometry;
            for(unsigned i=0;i<nv;++i) {double x,y,z; input>>x>>y>>z; geometry.node_pos_lst.insert(geometry.node_pos_lst.end(),{x,y,z});}
            for(unsigned i=0;i<nf;++i) {unsigned a,b,c; input>>a>>b>>c; geometry.face_point_ids.push_back({a,b,c});}
            if(!input) throw std::runtime_error("invalid mesh input");
            auto type=make_cell_type("probe",type_id,0.01,0.0,0.02,0.20,0.16);
            bodies.push_back(make_body(geometry,id,"myocardium",type));
        }
        reset_forces(bodies);
        for(auto& body:bodies) body.surface->apply_internal_forces(0.0);
        reset_forces(bodies);
        contact_face_face_via_coupling model(contact_parameters());
        assemble_contact(bodies,model);
        const std::filesystem::path output(argv[2]);
        if(std::filesystem::exists(output)) throw std::runtime_error("create-only output exists");
        std::filesystem::create_directories(output);
        std::ofstream stream(output/"nodes.csv");
        stream << std::setprecision(17) << "cell,node,x0,y0,z0,x,y,z,fx,fy,fz,area,curvature,pressure,coupled\n";
        for(auto& body:bodies) {
            const auto areas=nodal_areas(*body.surface);
            unsigned index=0;
            for(const auto& n:body.surface->get_node_lst()) {
                auto initial=body.initial_positions.at(n.get_persistent_id());
                auto p=node_position(n); auto f=node_force(n);
                stream<<body.surface->get_id()<<','<<index<<','<<initial[0]<<','<<initial[1]<<','<<initial[2]<<','<<p[0]<<','<<p[1]<<','<<p[2]<<','<<f[0]<<','<<f[1]<<','<<f[2]<<','<<areas[index]<<','<<n.get_curvature()<<','<<body.surface->get_pressure()<<','<<n.get_nb_coupled_nodes()<<'\n';
                ++index;
            }
        }
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n'; return 2;}
}
