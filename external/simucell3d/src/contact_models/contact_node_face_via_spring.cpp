#include "contact_node_face_via_spring.hpp"
#include <map>


#if CONTACT_MODEL_INDEX == 0 || defined(PRL_CONTACT_SPRING_PROBE)


/*
    This class contains the methods to compute the contact forces between pairs of nodes and faces belonging to adjacent cells. 
    The contact forces are calculated in the following way: 

    1 -> All the axias-aligned bounding boxes of the faces are computed and stored in a vector
    2 -> The faces are stored in an uniform space partitioning grid (USPG) based on their AABB
    3 -> For each point, we used the USPG to find the faces that are close to it
    4 -> We check if the point is within the AABB of the face
    5 -> If so, we compute the minimal distance between the point and the face
    6 -> The contact force is the computed based on the minimum distance and the contact parameters of the face

*/



//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
//The trivial constructor of the contact model
contact_node_face_via_spring::contact_node_face_via_spring(const global_simulation_parameters& sim_parameters) noexcept(false): contact_model_abstract(sim_parameters){

    //There are 2 interaction cutoffs, one for the adhesion and one for the repulsion. We use the max of the two to setup
    //the grid and the AABBs
    interaction_cutoff_ = std::max(sim_parameters.contact_cutoff_adhesion_, sim_parameters.contact_cutoff_repulsion_);
    interaction_cutoff_square_ = interaction_cutoff_*interaction_cutoff_;

    //The distance between 2 faces where the contact force is maximal, by default it's equal to interaction_cutoff_ / 2
    hardening_distance_ = sim_parameters.contact_cutoff_adhesion_ / 2.0;

}
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
//Find the contacts between the faces of the mesh and apply the contact forces
void contact_node_face_via_spring::run(const std::vector<cell_ptr>& cell_lst) noexcept{

        //Store all the faces of the mesh in a vector for easier access
        const size_t nb_faces = std::accumulate(cell_lst.begin(), cell_lst.end(), 0, [](size_t acc, const cell_ptr& c){return acc + c->get_nb_of_faces();});
        face_lst_.clear();
        face_lst_.reserve(nb_faces);
        
        //Give to each face a global id which is the index of the face in the face_lst_ vector
        size_t face_global_id = 0;
        for(cell_ptr c : cell_lst){
            for(auto& f : c->face_lst_){if(f.is_used()){
                face_lst_.push_back(&f);
                
                //Set the global id of all the faces
                f.global_face_id_ = face_global_id++;

                //Only compiles this section if the faces store their contact energies
                #if FACE_STORE_CONTACT_ENERGY
                    //Reset the adhesion and repulsion energies of the face
                    f.adhesion_energy_ = 0.0;
                    f.repulsion_energy_ = 0.0;
                #endif
    
            }}
        }

        //Compute the axis aligned bounding box of ech face and store it in the face_aabb_lst_ vector and update the grid dimensions
        update_face_aabbs(cell_lst);

        //Store all the faces of the mesh in a space partitionning grid
        store_face_in_uspg();
    
        //Find the faces that are within a distance below the contact cutoff and apply adhesive or repulsive forces
        resolve_contacts(cell_lst);
}
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------









//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
//Store all the faces in an unform space partitioning grid
void contact_node_face_via_spring::resolve_contacts(const std::vector<cell_ptr>& cell_lst) noexcept{


    //Loop over the cells in parallel
    #pragma omp parallel for
    for(size_t cell_id = 0; cell_id < cell_lst.size(); cell_id++){
        cell_ptr c1 = cell_lst[cell_id];

        //Loop over the nodes of the cell
        for(node& n: c1->node_lst_){

            if(n.is_used()){
                //Get the position of the node in the space partitioning grid
                const unsigned voxel_1_x = std::floor((n.pos().dx() - grid_.min_x_) / grid_.voxel_size_);
                const unsigned voxel_1_y = std::floor((n.pos().dy() - grid_.min_y_) / grid_.voxel_size_);
                const unsigned voxel_1_z = std::floor((n.pos().dz() - grid_.min_z_) / grid_.voxel_size_);

                //Get the ID of the voxel in the space partitionning grid
                const size_t voxel_id = grid_.get_voxel_index(voxel_1_x, voxel_1_y, voxel_1_z);
                assert(voxel_id < grid_.voxel_lst_.size());

                //Get the list of faces stored in this voxel
                for(face* f: grid_.voxel_lst_[voxel_id]){
                    assert(f != nullptr);

                    if(c1->get_id() != f->get_owner_cell()->get_id()){
 
                        //Check if the node is located in the AABB of the face
                        const size_t face_aabb_pos = f->global_face_id_ * 6;
                        if(aabb_intersection_check(face_aabb_pos, n.pos())){apply_contact_forces(c1, n, f);}
                    }
                }

            }  
        }
    }   
}
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------







//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
//Compute the distance between the 2 faces and apply the contact forces
void contact_node_face_via_spring::apply_contact_forces(cell_ptr c1, node& n, face* f) const noexcept{

    //Get the cell owning the face
    cell_ptr c2 = f->get_owner_cell();

    //Make sure that the nodes of the face are part of the cell number 2
    assert(f->n1_id_ < c2->node_lst_.size() && f->n2_id_ < c2->node_lst_.size() && f->n3_id_ < c2->node_lst_.size());

    //Get the node of the face
    node& f_n1 = c2->node_lst_[f->n1_id_];
    node& f_n2 = c2->node_lst_[f->n2_id_];
    node& f_n3 = c2->node_lst_[f->n3_id_];

    assert(f_n1.is_used() && f_n2.is_used() && f_n3.is_used());
    
    //Extract the position of the nodes of the face
    const vec3& f_n1_pos = f_n1.pos();
    const vec3& f_n2_pos = f_n2.pos();
    const vec3& f_n3_pos = f_n3.pos();

    //Get the minimal squared distance between the node and the face
    const auto [min_squared_distance, bary_pos] = contact_model_abstract::compute_node_triangle_distance(n.pos(), f_n1_pos, f_n2_pos, f_n3_pos);

  
    //Now that we know the minimal distance, we compute the resulting contact forces
    //If the distance between the 2 faces is below the interaction cutoff
    if(min_squared_distance < interaction_cutoff_square_ && min_squared_distance != 0.0){

        //The contact force vector goes from the closest point of approach on the face to the node
        const vec3 cpa_pos = f_n1_pos * bary_pos.dx() + f_n2_pos * bary_pos.dy() + f_n3_pos * bary_pos.dz();
        const vec3 cpa_f_to_node = n.pos() - cpa_pos;

        //Only compile this section if the faces store their contact energies
        #if FACE_STORE_CONTACT_ENERGY
            double adhesion_energy = 0.,    repulsion_energy = 0.;
        #endif

        //Get a reference to the types of the face
        const auto& face_type = c2->get_face_type(f->local_face_id_);

        //Determine if the contact is of adhesive or repulsive type based on the normal of the face
        bool adhesive_contact = (cpa_f_to_node.dot(f->normal_) > 0.0);

        //Reverse the direction of contact if the cell to which the face belongs is an ECM cell
        if (c1->get_cell_type_id() == 0 && c2->get_cell_type_id() == 1){adhesive_contact = !adhesive_contact;}

        //Do the same of the node belongs to a nucleus and the face to an epithelial cell
        if (c1->get_cell_type_id() == 3 && c2->get_cell_type_id() == 0){adhesive_contact = !adhesive_contact;}


        //Check that the faces have normals pointing in opposite directions
        if(adhesive_contact && min_squared_distance < interaction_cutoff_square_adhesion_){

            #if POLARIZATION_MODE_INDEX == 1
                //Indicate to the face that it is in contact with another cell
                c2->face_is_in_contact(f->local_face_id_, c1);
            #endif

            //Compute the distance
            double min_distance = std::sqrt(min_squared_distance);
            const double integration_region = f->area_;

            //Might change based on the hardening or softening regime
            double force_amplitude;

            //Hardening regime
            if(min_distance >= hardening_distance_){
                force_amplitude = face_type.adherence_strength_ * (interaction_cutoff_adhesion_ /min_distance - 1) * integration_region;

                #if FACE_STORE_CONTACT_ENERGY
                    adhesion_energy = integration_region * 0.5 * face_type.adherence_strength_ * (0.5 * interaction_cutoff_adhesion_ * interaction_cutoff_adhesion_ - pow(interaction_cutoff_adhesion_ - min_distance,2));
                #endif
            }

            //Softening regime
            else {
                force_amplitude =  face_type.adherence_strength_ * integration_region;

                #if FACE_STORE_CONTACT_ENERGY
                    adhesion_energy = 0.5 * face_type.adherence_strength_ * integration_region * min_distance * min_distance;
                #endif

            }

            #if FACE_STORE_CONTACT_ENERGY
                f->add_adhesion_energy(adhesion_energy);
            #endif

            //Apply the adhesion forces 
            const vec3 adhesion_force_vector =  cpa_f_to_node *  force_amplitude;

            //Linearly distribute the adhesion force onto the 3 nodes of the face
            f_n1.add_force(adhesion_force_vector * bary_pos.dx());
            f_n2.add_force(adhesion_force_vector * bary_pos.dy());
            f_n3.add_force(adhesion_force_vector * bary_pos.dz());

            //Apply the opposite force on the node
            n.add_force(adhesion_force_vector * -1.0);
        }
        


        //Repulsion regime
        if(!adhesive_contact && min_squared_distance < interaction_cutoff_square_repulsion_){

            #if POLARIZATION_MODE_INDEX == 1
            //Indicate to the face that it is in contact with another cell
            c2->face_is_in_contact(f->local_face_id_, c1);
            #endif

            //Compute the distance
            const double min_distance = std::sqrt(min_squared_distance);
            const double integration_region = f->area_;

            //Get a reference to the types of the face
            const auto& face_type = c2->get_face_type(f->local_face_id_);

            #if FACE_STORE_CONTACT_ENERGY
                repulsion_energy = 0.5 * face_type.repulsion_strength_ * integration_region * min_distance * min_distance;
                f->add_repulsion_energy(repulsion_energy);
            #endif

            //The force that will be distributed on the nodes of the 2 faces
            const vec3 repulsion_force_vector =  cpa_f_to_node  *  face_type.repulsion_strength_ * integration_region;

            //Apply the repulsion forces on the nodes of the 2 faces
            f_n1.add_force(repulsion_force_vector * bary_pos.dx());
            f_n2.add_force(repulsion_force_vector * bary_pos.dy());
            f_n3.add_force(repulsion_force_vector * bary_pos.dz());

            n.add_force(repulsion_force_vector * -1.0);   
        }
    }
}
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




// Symmetric nearest-surface quadrature. The native distance routine and piecewise
// spring law are retained; duplicate node/triangle hit weights are not retained.
contact_node_face_via_spring::surface_quadrature_audit
contact_node_face_via_spring::run_surface_quadrature(
    const std::vector<cell_ptr>& cells, double maximum_edge, double adhesion_scale, double positive_barrier_range) {
    if(!(maximum_edge > 0.0) || !std::isfinite(maximum_edge) ||
       !(adhesion_scale >= 0.0) || !std::isfinite(adhesion_scale) ||
       !(positive_barrier_range >= 0.0) || !std::isfinite(positive_barrier_range) ||
       positive_barrier_range > interaction_cutoff_repulsion_)
        throw std::invalid_argument("invalid surface contact quadrature parameters");
    surface_quadrature_audit audit;
    using bary_triangle = std::array<vec3, 3>;
    struct target_face {
        face* f;
        std::array<vec3,3> p;
        std::array<double,6> box;
        std::array<vec3,3> edge_pseudonormals;
        std::array<unsigned,3> node_ids{};
        vec3 normal{};
        std::array<vec3,3> area_gradient{};
        std::vector<vec3> sample_barycentrics;
        std::vector<vec3> sample_points;
        unsigned quadrature_depth=0;
        double quadrature_fraction=0;
        double quadrature_weight=0;
        double adherence_strength=0;
        double repulsion_strength=0;
    };
    struct target_cache {
        std::vector<target_face> faces;
        std::map<std::pair<unsigned,unsigned>,vec3> edge_normals;
        std::vector<vec3> vertex_normals;
        std::array<double,6> box{};
        bool has_faces=false;
    };
    const auto coordinates=[](const vec3& v){return std::array<double,3>{v.dx(),v.dy(),v.dz()};};
    const auto bounds=[&](const std::array<vec3,3>& p){
        std::array<double,6> box;
        for(unsigned axis=0;axis<3;++axis){
            box[axis]=std::min({coordinates(p[0])[axis],coordinates(p[1])[axis],coordinates(p[2])[axis]});
            box[axis+3]=std::max({coordinates(p[0])[axis],coordinates(p[1])[axis],coordinates(p[2])[axis]});
        }return box;
    };
    const double cutoff=std::max(interaction_cutoff_adhesion_,interaction_cutoff_repulsion_);
    face_lst_.clear();
    std::vector<std::size_t> global_to_cell,global_to_local;
    for(std::size_t cell_index=0;cell_index<cells.size();++cell_index){
        std::size_t local_index=0;
        for(auto& current_face:cells[cell_index]->face_lst_)if(current_face.is_used()){
            current_face.global_face_id_=face_lst_.size();
            face_lst_.push_back(&current_face);
            global_to_cell.push_back(cell_index);
            global_to_local.push_back(local_index++);
        }
    }
    update_face_aabbs(cells);
    store_face_in_uspg();
    const auto box_distance_square=[](const std::array<double,6>& box,const std::array<double,3>& point){
        double result=0;
        for(unsigned axis=0;axis<3;++axis){
            const double delta=std::max({box[axis]-point[axis],point[axis]-box[axis+3],0.0});
            result+=delta*delta;
        }
        return result;
    };
    std::vector<target_cache> target_caches(cells.size());
    for(std::size_t target_index=0;target_index<cells.size();++target_index){
        const auto& target=cells[target_index];
        auto& cache=target_caches[target_index];
        cache.vertex_normals.assign(target->node_lst_.size(),vec3(0,0,0));
        // Feature pseudonormals avoid using an arbitrary coplanar face normal
        // at a rim. A point outside an edge must not flip to penetration merely
        // because another triangle wins a floating-point closest-point tie.
        for(auto& f:target->face_lst_)if(f.is_used()){
            const auto ids=f.get_node_ids();
            std::array<vec3,3> p={target->node_lst_[ids[0]].pos(),target->node_lst_[ids[1]].pos(),target->node_lst_[ids[2]].pos()};
            const auto box=bounds(p);
            cache.faces.push_back({&f,p,box,{}});
            auto& cached_face=cache.faces.back();
            cached_face.node_ids=ids;
            const vec3 area_vector=(p[1]-p[0]).cross(p[2]-p[0]);
            const double twice_area=area_vector.norm();
            if(!(twice_area>1e-15))throw std::runtime_error("degenerate contact source triangle");
            cached_face.normal=area_vector/twice_area;
            cached_face.area_gradient={
                (p[1]-p[2]).cross(cached_face.normal)*.5,
                (p[2]-p[0]).cross(cached_face.normal)*.5,
                (p[0]-p[1]).cross(cached_face.normal)*.5
            };
            double edge=std::max({(p[1]-p[0]).norm(),(p[2]-p[1]).norm(),(p[0]-p[2]).norm()});
            unsigned depth=0;
            while(edge>maximum_edge){
                if(++depth>8)throw std::runtime_error("contact quadrature subdivision budget exceeded");
                edge*=.5;
            }
            std::size_t patch_count=1;
            for(unsigned level=0;level<depth;++level)patch_count*=4;
            cached_face.quadrature_depth=depth;
            cached_face.quadrature_fraction=0.5/(3.0*patch_count);
            cached_face.quadrature_weight=0.5*twice_area*cached_face.quadrature_fraction;
            if(cells.size()>4){
                std::vector<bary_triangle> patches={{{vec3(1,0,0),vec3(0,1,0),vec3(0,0,1)}}};
                for(unsigned level=0;level<depth;++level){
                std::vector<bary_triangle> refined;refined.reserve(patches.size()*4);
                for(const auto& triangle:patches){
                    const auto ab=(triangle[0]+triangle[1])*.5,bc=(triangle[1]+triangle[2])*.5,ca=(triangle[2]+triangle[0])*.5;
                    refined.push_back({triangle[0],ab,ca});refined.push_back({ab,triangle[1],bc});
                    refined.push_back({ca,bc,triangle[2]});refined.push_back({ab,bc,ca});
                    }patches=std::move(refined);
                }
                cached_face.sample_barycentrics.reserve(3*patches.size());
                cached_face.sample_points.reserve(3*patches.size());
                for(const auto& patch:patches)for(unsigned sample=0;sample<3;++sample){
                    const vec3 source_bary=patch[sample]*(2.0/3.0)+(patch[(sample+1)%3]+patch[(sample+2)%3])*(1.0/6.0);
                    const auto bary=coordinates(source_bary);
                    cached_face.sample_barycentrics.push_back(source_bary);
                    cached_face.sample_points.push_back(p[0]*bary[0]+p[1]*bary[1]+p[2]*bary[2]);
                }
            }
            const auto& material=target->get_face_type(f.local_face_id_);
            cached_face.adherence_strength=material.adherence_strength_;
            cached_face.repulsion_strength=material.repulsion_strength_;
            if(!cache.has_faces){cache.box=box;cache.has_faces=true;}
            else for(unsigned axis=0;axis<3;++axis){
                cache.box[axis]=std::min(cache.box[axis],box[axis]);
                cache.box[axis+3]=std::max(cache.box[axis+3],box[axis+3]);
            }
            for(unsigned i=0;i<3;++i){
                const unsigned j=(i+1)%3,k=(i+2)%3;
                const auto key=std::minmax(ids[i],ids[j]);
                auto iter=cache.edge_normals.find(key);
                if(iter==cache.edge_normals.end())cache.edge_normals.emplace(key,f.normal_);
                else iter->second=iter->second+f.normal_;
                const vec3 u=p[j]-p[i],v=p[k]-p[i];
                const double cosine=std::max(-1.0,std::min(1.0,u.dot(v)/(u.norm()*v.norm())));
                cache.vertex_normals[ids[i]]=cache.vertex_normals[ids[i]]+f.normal_*std::acos(cosine);
            }
        }
        for(auto& cached_face:cache.faces){
            const auto ids=cached_face.f->get_node_ids();
            for(unsigned opposite=0;opposite<3;++opposite){
                const unsigned first=ids[(opposite+1)%3],second=ids[(opposite+2)%3];
                cached_face.edge_pseudonormals[opposite]=cache.edge_normals.at(std::minmax(first,second));
            }
        }
    }
    // The native grid stores all faces in one list per voxel.  Scanning that
    // list once for every target cell repeats the same pointer and owner tests.
    // Keep the exact grid candidates, but group them once by target cell.
    std::vector<std::vector<std::size_t>> grouped_voxel_faces;
    if(cells.size()>4){
        grouped_voxel_faces.resize(grid_.voxel_lst_.size()*cells.size());
        for(std::size_t voxel_index=0;voxel_index<grid_.voxel_lst_.size();++voxel_index)
            for(face* candidate_face:grid_.voxel_lst_[voxel_index]){
                const std::size_t global_index=candidate_face->global_face_id_;
                grouped_voxel_faces[voxel_index*cells.size()+global_to_cell[global_index]].push_back(global_index);
            }
    }
    for(std::size_t source_index=0;source_index<cells.size();++source_index)
    for(std::size_t target_index=0;target_index<cells.size();++target_index) {
        if(source_index==target_index)continue;
        const auto& source=cells[source_index];
        const auto& target=cells[target_index];
        const auto& source_cache=target_caches[source_index];
        const auto& cache=target_caches[target_index];
        bool cells_nearby=source_cache.has_faces && cache.has_faces;
        for(unsigned axis=0;axis<3;++axis)
            cells_nearby=cells_nearby
                && source_cache.box[axis]<=cache.box[axis+3]+cutoff
                && source_cache.box[axis+3]>=cache.box[axis]-cutoff;
        if(!cells_nearby)continue;
        const auto& target_faces=cache.faces;
        const auto& vertex_normals=cache.vertex_normals;
        for(const auto& source_face:source_cache.faces){
            const auto& ids=source_face.node_ids;
            const auto& p=source_face.p;
            const auto& source_box=source_face.box;
            std::vector<const target_face*> linear_candidates;
            if(cells.size()<=4){
                for(const auto& candidate:target_faces){
                    bool nearby=true;
                    for(unsigned axis=0;axis<3;++axis)
                        nearby=nearby
                            && source_box[axis]<=candidate.box[axis+3]+cutoff
                            && source_box[axis+3]>=candidate.box[axis]-cutoff;
                    if(nearby)linear_candidates.push_back(&candidate);
                }
                if(linear_candidates.empty())continue;
            }
            const auto& area_gradient=source_face.area_gradient;
            const double fraction=source_face.quadrature_fraction;
            const double weight=source_face.quadrature_weight;
            const auto process_sample=[&](const vec3& source_bary,const vec3& q){
                const auto sb=coordinates(source_bary);
                const auto qc=coordinates(q);std::size_t best_index=target_faces.size();
                double distance_square=cutoff*cutoff;vec3 target_bary;
                if(cells.size()<=4){
                    for(const auto* candidate:linear_candidates){
                        const std::size_t face_index=static_cast<std::size_t>(candidate-target_faces.data());
                        if(box_distance_square(candidate->box,qc)>distance_square)continue;
                        const auto result=compute_node_triangle_distance(q,candidate->p[0],candidate->p[1],candidate->p[2]);
                        if(result.first<distance_square){
                            distance_square=result.first;target_bary=result.second;best_index=face_index;
                        }
                    }
                }else{
                    const std::size_t voxel_index=grid_.get_voxel_index(q);
                    const auto& voxel_candidates=grouped_voxel_faces[voxel_index*cells.size()+target_index];
                    for(const std::size_t global_index:voxel_candidates){
                        if(!aabb_intersection_check(global_index*6,q))continue;
                        const std::size_t face_index=global_to_local[global_index];
                        const auto& candidate=target_faces[face_index];
                        const auto result=compute_node_triangle_distance(q,candidate.p[0],candidate.p[1],candidate.p[2]);
                        if(result.first<distance_square || (result.first==distance_square && face_index<best_index)){
                            distance_square=result.first;target_bary=result.second;best_index=face_index;
                        }
                    }
                }
                const target_face* best=best_index<target_faces.size()?&target_faces[best_index]:nullptr;
                if(!best)return;
                const auto tb=coordinates(target_bary);
                const vec3 delta=q-(best->p[0]*tb[0]+best->p[1]*tb[1]+best->p[2]*tb[2]);
                const double distance=std::sqrt(distance_square);
                const auto& target_ids=best->node_ids;
                std::array<unsigned,3> feature{};unsigned feature_count=0;
                for(unsigned i=0;i<3;++i)if(tb[i]>1e-9)feature[feature_count++]=target_ids[i];
                vec3 sign_normal=best->normal;
                if(feature_count==1)sign_normal=vertex_normals[feature[0]];
                if(feature_count==2){
                    unsigned opposite=0;while(opposite<3 && tb[opposite]>1e-9)++opposite;
                    sign_normal=best->edge_pseudonormals[opposite];
                }
                const double sign=delta.dot(sign_normal)>=0.0?1.0:-1.0;
                const double gap=sign*distance;
                const double ka=best->adherence_strength*adhesion_scale,kr=best->repulsion_strength;
                const double c=interaction_cutoff_adhesion_;
                double potential=0.0,slope=0.0;
                if(positive_barrier_range>0.0 && gap<=1e-12)
                    throw std::runtime_error("positive-gap barrier requires disjoint surfaces");
                if(gap<0.0){
                    if(distance>=interaction_cutoff_repulsion_)return;
                    potential=.5*kr*gap*gap-ka*c*c/4.0;slope=kr*gap;
                }else if(gap<c*.5){potential=.5*ka*gap*gap-ka*c*c/4.0;slope=ka*gap;}
                else if(gap<c){potential=-.5*ka*(c-gap)*(c-gap);slope=ka*(c-gap);}
                else if(positive_barrier_range==0.0 || gap>=positive_barrier_range)return;
                // TriMem-inspired normalized surface potential; adhesion remains separate.
                // Include its area derivative below, not only the normal distance force.
                if(positive_barrier_range>0.0 && gap<positive_barrier_range){
                    const double x=gap/positive_barrier_range;
                    const double repulsion=kr*positive_barrier_range*positive_barrier_range*std::exp(x/(x-1.0))/(x*x);
                    potential+=repulsion;
                    slope+=repulsion/positive_barrier_range*(-1.0/((x-1.0)*(x-1.0))-2.0/x);
                }
                audit.energy+=weight*potential;audit.support_area+=weight;++audit.active_samples;
                const vec3 gradient=distance>1e-15?delta*(weight*slope*sign/distance):vec3(0,0,0);
                for(unsigned vertex=0;vertex<3;++vertex){
                    source->node_lst_[ids[vertex]].add_force(gradient*(-sb[vertex])-area_gradient[vertex]*(fraction*potential));
                    target->node_lst_[target_ids[vertex]].add_force(gradient*tb[vertex]);
                }
            };
            if(cells.size()<=4){
                std::vector<bary_triangle> patches={{{vec3(1,0,0),vec3(0,1,0),vec3(0,0,1)}}};
                for(unsigned level=0;level<source_face.quadrature_depth;++level){
                    std::vector<bary_triangle> refined;refined.reserve(patches.size()*4);
                    for(const auto& triangle:patches){
                        const auto ab=(triangle[0]+triangle[1])*.5,bc=(triangle[1]+triangle[2])*.5,ca=(triangle[2]+triangle[0])*.5;
                        refined.push_back({triangle[0],ab,ca});refined.push_back({ab,triangle[1],bc});
                        refined.push_back({ca,bc,triangle[2]});refined.push_back({ab,bc,ca});
                    }patches=std::move(refined);
                }
                for(const auto& patch:patches)for(unsigned sample=0;sample<3;++sample){
                    const vec3 source_bary=patch[sample]*(2.0/3.0)+(patch[(sample+1)%3]+patch[(sample+2)%3])*(1.0/6.0);
                    const auto sb=coordinates(source_bary);
                    process_sample(source_bary,p[0]*sb[0]+p[1]*sb[1]+p[2]*sb[2]);
                }
            }else for(std::size_t sample=0;sample<source_face.sample_barycentrics.size();++sample){
                process_sample(source_face.sample_barycentrics[sample],source_face.sample_points[sample]);
            }
        }
    }
    return audit;
}

#endif

