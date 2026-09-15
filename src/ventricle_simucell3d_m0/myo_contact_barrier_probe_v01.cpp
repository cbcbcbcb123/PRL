#include "m0_model.hpp"
#include "contact_node_face_via_spring.hpp"
#include "surface_separation_guard.hpp"

using namespace prl::ventricle::m0;

int main(int argc, char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="--geometry-self-test"){
            using namespace prl::contact_safety;
            const Triangle a={vec3(0,0,0),vec3(1,0,0),vec3(0,1,0)};
            const Triangle crossed={vec3(.2,.2,-1),vec3(.2,.2,1),vec3(.8,.2,1)};
            const Triangle coplanar={vec3(.1,.1,0),vec3(.4,.1,0),vec3(.1,.4,0)};
            Triangle lifted=a;for(auto& p:lifted)p=p+vec3(0,0,.07);
            if(triangle_distance(a,crossed)>1e-10 || triangle_distance(a,coplanar)>1e-10 || std::abs(triangle_distance(a,lifted)-.07)>1e-10)
                throw std::runtime_error("triangle distance regression failed");
            if(std::abs(segment_distance(vec3(-1,0,0),vec3(1,0,0),vec3(0,-1,.03),vec3(0,1,.03))-.03)>1e-10)
                throw std::runtime_error("interior edge-edge distance failed");
            Separation separation;separation.intercell=.07;separation.nonincident=1.;separation.min_height=1.;
            const double accepted=safe_increment(separation,10.,1.);
            if(!(20.*accepted<.07))throw std::runtime_error("swept displacement bound failed");
            std::cout<<"triangle crossing, coplanar overlap, separation, edge-edge, swept bound: passed\n";return 0;
        }
        if(argc < 4 || argc > 7) throw std::runtime_error("usage: probe mesh_input output_directory type_id [quadrature [adhesion_scale [quadrature_edge]]]");
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
        contact_node_face_via_spring model(contact_parameters());
        std::vector<cell_ptr> cells;
        for(auto& body:bodies) {body.surface->set_local_id(static_cast<unsigned>(cells.size())); cells.push_back(body.surface);}
        contact_node_face_via_spring::surface_quadrature_audit audit;
        const bool quadrature=argc>=5 && std::string(argv[4])=="quadrature";
        const bool geometry_only=argc>=5 && std::string(argv[4])=="geometry";
        if(argc>=5 && !quadrature && !geometry_only)throw std::runtime_error("unknown contact strategy");
        const auto separation=prl::contact_safety::measure(cells);
        if(geometry_only){
            std::cout<<std::setprecision(17)<<"{\"intercell_distance\":"<<separation.intercell<<",\"nonincident_distance\":"<<separation.nonincident<<"}\n";
            return separation.intercell>1e-8 && separation.nonincident>1e-8?0:3;
        }
        if(separation.intercell<=1e-8)throw std::runtime_error("intersecting initial mesh");
        if(quadrature)audit=model.run_surface_quadrature(cells,argc==7?std::stod(argv[6]):.20,argc>=6?std::stod(argv[5]):1.0,.14);
        else model.run(cells);
        const std::filesystem::path output(argv[2]);
        if(std::filesystem::exists(output)) throw std::runtime_error("create-only output exists");
        std::filesystem::create_directories(output);
        if(quadrature){
            std::ofstream metadata(output/"contact.json");
            metadata<<std::setprecision(17)<<"{\"contact_energy\":"<<audit.energy
                <<",\"quadrature_support_area\":"<<audit.support_area
                <<",\"active_samples\":"<<audit.active_samples<<"}\n";
        }
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
