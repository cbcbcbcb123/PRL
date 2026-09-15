#include "node.hpp"

#include <utility>


node::node() noexcept {
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_);
    #endif
}

node::node(const unsigned node_id) noexcept : node_id_(node_id) {
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_);
    #endif
}

node::node(const node& other) noexcept {
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_);
    #endif
    *this = other;
}

node::node(node&& other) noexcept {
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_);
    #endif
    *this = std::move(other);
}

node& node::operator=(const node& other) noexcept {
    if(this == &other) return *this;
    node_id_ = other.node_id_;
    persistent_id_ = other.persistent_id_;
    is_used_ = other.is_used_;
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        normal_ = other.normal_;
        curvature_ = other.curvature_;
    #endif
    #if CONTACT_MODEL_INDEX == 1
        coupled_node_ = other.coupled_node_;
        squared_distance_to_closest_node_ = other.squared_distance_to_closest_node_;
    #elif CONTACT_MODEL_INDEX == 2
        coupled_nodes_map_ = other.coupled_nodes_map_;
    #endif
    pos_ = other.pos_;
    force_ = other.force_;
    #if DYNAMIC_MODEL_INDEX == 0
        momentum_ = other.momentum_;
    #endif
    return *this;
}

node& node::operator=(node&& other) noexcept {
    if(this == &other) return *this;
    node_id_ = other.node_id_;
    persistent_id_ = other.persistent_id_;
    is_used_ = other.is_used_;
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        normal_ = std::move(other.normal_);
        curvature_ = other.curvature_;
    #endif
    #if CONTACT_MODEL_INDEX == 1
        coupled_node_ = std::move(other.coupled_node_);
        squared_distance_to_closest_node_ = other.squared_distance_to_closest_node_;
    #elif CONTACT_MODEL_INDEX == 2
        coupled_nodes_map_ = std::move(other.coupled_nodes_map_);
    #endif
    pos_ = std::move(other.pos_);
    force_ = std::move(other.force_);
    #if DYNAMIC_MODEL_INDEX == 0
        momentum_ = std::move(other.momentum_);
    #endif
    return *this;
}

node::~node() {
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_destroy_lock(&lock_);
    #endif
}



//Trivial constructor
//---------------------------------------------------------------------------------------------------------
node::node(const double dx, const double dy, const double dz, const unsigned node_id) noexcept :node_id_(node_id){

    //Check the coordinates of the node
    assert(std::isfinite(dx) && std::isfinite(dy) && std::isfinite(dz));

    //Set the position of the node
    pos_.translate(dx, dy, dz);


    //Overdamped equations of motion solved with the improved euler scheme
    #if DYNAMIC_MODEL_INDEX == 2

        //The previous position is the starting position
        previous_pos_.translate(dx, dy, dz);
    #endif 

    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_); // Initialize the lock in the constructor
    #endif

}

node::node(const vec3& pos, const unsigned node_id) noexcept{
    node_id_ = node_id;
    pos_ = pos;

    //Overdamped equations of motion solved with the improved euler scheme
    #if DYNAMIC_MODEL_INDEX == 2
     
        //The previous position is the starting position
        previous_pos_ = pos;
    #endif 

    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        omp_init_lock(&lock_); // Initialize the lock in the constructor
    #endif
}

//---------------------------------------------------------------------------------------------------------
//Reset the vectors owned by the node
void node::reset() noexcept {
    assert(is_used_ = true);

    pos_.reset();
    force_.reset();


    #if CONTACT_MODEL_INDEX == 1
        //Remove the coupling to the face
        coupled_node_.reset();

    #endif



    #if CONTACT_MODEL_INDEX == 2
        //Remove the coupling to the face
        coupled_nodes_map_.clear();

    #endif

    //Overdamped equations of motion solved with the improved euler scheme
    #if DYNAMIC_MODEL_INDEX == 0
        momentum_.reset();
    
    #elif DYNAMIC_MODEL_INDEX == 2
    
        previous_pos_.reset();
        previous_force_.reset();
    #endif 

    //Indicate that the node is not used by the cell anymore
    is_used_ = false;
}
//---------------------------------------------------------------------------------------------------------



//---------------------------------------------------------------------------------------------------------
//Check if the 2 nodes have the same id
bool node::operator==(const node& n) const noexcept {return node_id_ == n.get_local_id();}

bool node::operator!=(const node& n) const noexcept{return node_id_ != n.get_local_id();}
//---------------------------------------------------------------------------------------------------------

//The substraction of 2 nodes returns a vector
vec3 node::operator-(const node& n) const noexcept{return pos_ - n.pos();}

