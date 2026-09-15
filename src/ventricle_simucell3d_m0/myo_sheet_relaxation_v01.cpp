// Application assembly only: existing myocardium loads and unique core integration/contact.
#define main preserved_bioform_entrypoint
#include "../ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp"
#undef main
#include "contact_node_face_via_spring.hpp"

struct SheetCell {
    cell_ptr surface;
    std::vector<Vector3> initial;
    std::vector<bool> fixed;
    double volume0;
};
struct SheetAssembly {
    std::vector<std::vector<Vector3>> passive,contact,shape,total,reaction;
    double contact_energy=0,support=0,passive_energy=0,max_free_force=0,max_speed=0;
};

int main(int argc,char** argv){
    std::filesystem::path output;
    try {
        if(argc!=7)throw std::runtime_error("usage: mesh output dt steps free|clamp wall_seconds");
        omp_set_num_threads(1);output=argv[2];
        const double dt=std::stod(argv[3]),wall_limit=std::stod(argv[6]);const unsigned steps=std::stoul(argv[4]);
        const bool clamped=std::string(argv[5])=="clamp";
        if(!(dt>0 && std::isfinite(dt)) || steps<4 || !(wall_limit>0))throw std::runtime_error("invalid run parameters");
        if(std::filesystem::exists(output))throw std::runtime_error("create-only output exists");
        std::filesystem::create_directories(output);
        const auto began=std::chrono::steady_clock::now();
        std::ifstream input(argv[1]);unsigned count;input>>count;
        if(!input || (count!=2 && count!=16) || (clamped && count!=16))throw std::runtime_error("invalid cell count/boundary combination");
        std::vector<SheetCell> bodies;std::vector<cell_ptr> cells;
        for(unsigned cid=0;cid<count;++cid){
            unsigned nv,nf;input>>nv>>nf;mesh geometry;
            for(unsigned i=0;i<nv;++i){double x,y,z;input>>x>>y>>z;geometry.node_pos_lst.insert(geometry.node_pos_lst.end(),{x,y,z});}
            for(unsigned i=0;i<nf;++i){unsigned a,b,c;input>>a>>b>>c;geometry.face_point_ids.push_back({a,b,c});}
            if(!input)throw std::runtime_error("invalid geometry input");
            const auto measured=measure_mesh(geometry);auto type=make_myocardium_type(std::pow(measured.area,3)/std::pow(measured.signed_volume,2));
            type->face_types_[0].adherence_strength_=.04;type->face_types_[0].repulsion_strength_=.16;
            SheetCell body;body.surface=std::make_shared<cell>(geometry,cid,type);body.surface->initialize_cell_properties();body.surface->set_local_id(cid);
            body.volume0=body.surface->get_volume();double low=1e30,high=-1e30;
            for(const auto& n:body.surface->get_node_lst()){body.initial.push_back(node_position(n));low=std::min(low,node_position(n)[0]);high=std::max(high,node_position(n)[0]);}
            for(const auto& p:body.initial)body.fixed.push_back(clamped && ((cid%4==0 && std::abs(p[0]-low)<1e-8)||(cid%4==3 && std::abs(p[0]-high)<1e-8)));
            cells.push_back(body.surface);bodies.push_back(std::move(body));
        }
        global_simulation_parameters parameters;parameters.min_edge_len_=.4;parameters.contact_cutoff_adhesion_=.35;parameters.contact_cutoff_repulsion_=.35;
        contact_node_face_via_spring contact(parameters);RunConfig shape_config=parse_config("FULL",320,dt,.060);
        std::ofstream nodes(output/"nodes.csv"),faces(output/"faces.csv"),states(output/"states.csv"),cell_states(output/"cells.csv"),audits(output/"step_audits.csv");
        nodes<<"snapshot,step,coordinate,cell,node,x,y,z,fx,fy,fz,cfx,cfy,cfz,sfx,sfy,sfz,rfx,rfy,rfz,area,curvature,pressure,fixed,x0,y0,z0\n";
        faces<<"cell,face,a,b,c\n";states<<"snapshot,step,coordinate,max_free_force,max_volume_error,min_angle,max_fixed_displacement,contact_energy,contact_support_area,passive_energy\n";
        cell_states<<"snapshot,cell,volume,target_volume,length,width,thickness,pressure\n";
        audits<<"step,coordinate,max_free_force,max_volume_error,min_angle,max_fixed_displacement,work_residual,shape_work,dissipation,contact_energy\n";
        for(unsigned cid=0;cid<count;++cid)for(const auto& f:cells[cid]->get_face_lst()){const auto ids=f.get_node_ids();faces<<cid<<','<<f.get_local_id()<<','<<ids[0]<<','<<ids[1]<<','<<ids[2]<<'\n';}
        const auto assemble=[&](){
            SheetAssembly result;
            for(auto& body:bodies){
                static_cast<void>(prl::cell_engine::refresh_surface_geometry(*body.surface,body.surface->get_mesh_revision()));reset_forces(*body.surface);body.surface->apply_internal_forces(0.0);
                result.passive.push_back(capture_forces(*body.surface));result.passive_energy+=passive_energy(*body.surface);
                const auto raw=cytoskeleton_load(*body.surface,shape_config,1.0);std::vector<Vector3> zeros(raw.nodal_forces.size(),Vector3{});
                result.shape.push_back(project_shape_velocity(*body.surface,zeros,raw.nodal_forces).effective_total_forces);
            }
            const auto contact_audit=contact.run_surface_quadrature(cells,.10,1.0);result.contact_energy=contact_audit.energy;result.support=contact_audit.support_area;
            for(unsigned cid=0;cid<count;++cid){
                auto combined=capture_forces(*cells[cid]);std::vector<Vector3> cf(combined.size()),total(combined.size()),reaction(combined.size());const auto areas=nodal_areas(*cells[cid]);
                for(unsigned i=0;i<combined.size();++i){
                    cf[i]=subtract(combined[i],result.passive[cid][i]);total[i]=add(combined[i],result.shape[cid][i]);
                    if(bodies[cid].fixed[i]){reaction[i]=scale(total[i],-1);total[i]=Vector3{};}
                    const double force=norm(total[i]);if(!std::isfinite(force)||!(areas[i]>0))throw std::runtime_error("nonfinite force or invalid nodal area");
                    result.max_free_force=std::max(result.max_free_force,force);result.max_speed=std::max(result.max_speed,force/areas[i]);
                }
                result.contact.push_back(cf);result.total.push_back(total);result.reaction.push_back(reaction);
            }return result;
        };
        const auto geometry_metrics=[&](){
            std::array<double,4> values{0.,180.,0.,1e30};
            for(unsigned cid=0;cid<count;++cid){
                values[0]=std::max(values[0],std::abs(cells[cid]->get_volume()/bodies[cid].volume0-1));values[1]=std::min(values[1],minimum_triangle_angle_degrees(*cells[cid]));
                for(unsigned i=0;i<bodies[cid].initial.size();++i)if(bodies[cid].fixed[i])values[2]=std::max(values[2],norm(subtract(node_position(cells[cid]->get_node_lst()[i]),bodies[cid].initial[i])));
                for(const auto& f:cells[cid]->get_face_lst()){const auto ids=f.get_node_ids();for(unsigned i=0;i<3;++i)values[3]=std::min(values[3],norm(subtract(node_position(cells[cid]->get_node_lst()[ids[i]]),node_position(cells[cid]->get_node_lst()[ids[(i+1)%3]]))));}
            }return values;
        };
        unsigned snapshot=0;double coordinate=0.0;const double end_coordinate=dt*steps;double next_snapshot=end_coordinate/4.0;
        const auto save=[&](unsigned step,const SheetAssembly& assembly){
            const auto gm=geometry_metrics();states<<std::setprecision(17)<<snapshot<<','<<step<<','<<coordinate<<','<<assembly.max_free_force<<','<<gm[0]<<','<<gm[1]<<','<<gm[2]<<','<<assembly.contact_energy<<','<<assembly.support<<','<<assembly.passive_energy<<'\n';
            for(unsigned cid=0;cid<count;++cid){
                const auto areas=nodal_areas(*cells[cid]);Vector3 low{1e30,1e30,1e30},high{-1e30,-1e30,-1e30};
                for(unsigned i=0;i<areas.size();++i){const auto& n=cells[cid]->get_node_lst()[i];const auto p=node_position(n);nodes<<std::setprecision(17)<<snapshot<<','<<step<<','<<coordinate<<','<<cid<<','<<i;
                    for(double value:p)nodes<<','<<value;for(const auto* field:{&assembly.total[cid][i],&assembly.contact[cid][i],&assembly.shape[cid][i],&assembly.reaction[cid][i]})for(double value:*field)nodes<<','<<value;
                    nodes<<','<<areas[i]<<','<<n.get_curvature()<<','<<cells[cid]->get_pressure()<<','<<bodies[cid].fixed[i];for(double value:bodies[cid].initial[i])nodes<<','<<value;nodes<<'\n';
                    for(unsigned axis=0;axis<3;++axis){low[axis]=std::min(low[axis],p[axis]);high[axis]=std::max(high[axis],p[axis]);}
                }
                cell_states<<std::setprecision(17)<<snapshot<<','<<cid<<','<<cells[cid]->get_volume()<<','<<bodies[cid].volume0<<','<<high[0]-low[0]<<','<<high[1]-low[1]<<','<<high[2]-low[2]<<','<<cells[cid]->get_pressure()<<'\n';
            }++snapshot;nodes.flush();states.flush();cell_states.flush();
        };
        auto assembly=assemble();save(0,assembly);double cumulative_shape_work=0,cumulative_dissipation=0;unsigned completed=0;
        for(unsigned step=1;coordinate<end_coordinate-1e-12;++step){
            const double increment=std::min({dt,end_coordinate-coordinate,next_snapshot-coordinate});
            const auto gm=geometry_metrics();
            if(increment*assembly.max_speed>.08*gm[3]){save(step-1,assembly);throw std::runtime_error("step motion exceeded frozen edge fraction");}
            if(std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()>wall_limit){save(step-1,assembly);throw std::runtime_error("frozen wall budget exhausted");}
            double work_residual=0,shape_work=0,dissipation=0;
            for(unsigned cid=0;cid<count;++cid){
                const auto area=nodal_areas(*cells[cid]);std::vector<Vector3> additional(area.size());
                for(unsigned i=0;i<area.size();++i){additional[i]=add(assembly.shape[cid][i],assembly.reaction[cid][i]);shape_work+=increment*dot(assembly.shape[cid][i],assembly.total[cid][i])/area[i];}
                const auto audit=prl::cell_engine::advance_surface_overdamped(*cells[cid],cells[cid]->get_mesh_revision(),increment,SurfaceDampingLaw{SurfaceDampingMeasure::barycentric_dual_area,1.0},as_surface_forces(*cells[cid],additional));
                dissipation+=audit.viscous_dissipation;work_residual=std::max(work_residual,std::abs(audit.work_dissipation_residual)/std::max({std::abs(audit.total_force_work),std::abs(audit.viscous_dissipation),kTiny}));
            }
            completed=step;coordinate+=increment;cumulative_shape_work+=shape_work;cumulative_dissipation+=dissipation;assembly=assemble();const auto after=geometry_metrics();
            audits<<std::setprecision(17)<<step<<','<<coordinate<<','<<assembly.max_free_force<<','<<after[0]<<','<<after[1]<<','<<after[2]<<','<<work_residual<<','<<shape_work<<','<<dissipation<<','<<assembly.contact_energy<<'\n';audits.flush();
            if(coordinate>=next_snapshot-1e-12){save(step,assembly);next_snapshot+=end_coordinate/4.0;}
            if(after[0]>.05 || after[1]<8 || after[2]>1e-10 || work_residual>1e-10){save(step,assembly);throw std::runtime_error("geometry, clamp or step-work safety gate failed");}
            if(step%25==0)std::cout<<"step "<<step<<" / "<<steps<<" max_force "<<assembly.max_free_force<<std::endl;
        }
        std::ofstream report(output/"run.json");report<<std::setprecision(17)<<"{\"execution_status\":\"passed\",\"completed_steps\":"<<completed<<",\"snapshots\":"<<snapshot<<",\"shape_work\":"<<cumulative_shape_work<<",\"dissipation\":"<<cumulative_dissipation<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()<<",\"static_equilibrium\":\"not_adjudicated\"}\n";
        return 0;
    }catch(const std::exception& e){if(!output.empty() && std::filesystem::exists(output)){std::ofstream failure(output/"failure.txt");failure<<e.what()<<'\n';}std::cerr<<e.what()<<'\n';return 2;}
}
