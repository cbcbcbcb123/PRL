#include "local_mesh_refiner_tester.hpp"

#include <cstdint>


namespace {

struct recorded_remesh_event {
    prl::core::RemeshEvent event;
    prl::core::SurfaceMeshSnapshot before;
    prl::core::SurfaceMeshSnapshot after;
};

class recording_remesh_sink final : public prl::core::RemeshEventSink {
public:
    void on_remesh(
        const prl::core::RemeshEvent& event,
        const prl::core::SurfaceMeshSnapshot& before,
        const prl::core::SurfaceMeshSnapshot& after
    ) override {
        records.push_back({event, before, after});
    }

    std::vector<recorded_remesh_event> records;
};

std::vector<std::uint64_t> sorted_vertex_ids(const prl::core::SurfaceMeshSnapshot& snapshot) {
    std::vector<std::uint64_t> ids;
    ids.reserve(snapshot.vertices.size());
    for (const auto& vertex : snapshot.vertices) ids.push_back(vertex.persistent_id);
    std::sort(ids.begin(), ids.end());
    return ids;
}

} // namespace





//Unit tests for the local_mesh_refiner class

int local_mesh_refiner_tester::can_be_merged_test(){
    
//          A
//       / /|\ ＼     
//     /  / | \  ＼    
//   /  6/  |  \ 3 ＼  
//  F__E/ 1 | 2 \D__＼C
//  \   \   |   /   ／
//    \5 \  |  / 4／  
//      \ \ | / ／    
//       \ \|/／      
//          B
//   


   //Create the geometry shown above

    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,   //Node A 0
        0., -2., 0.,   //Node B 1 
        2., -1., 0.,   //Node C 2
        1., -1., 0.,   //Node D 3
       -1., -1., 0.,   //Node E 4
       -2., -1., 0.,   //Node F 5

        0.,  0., -1.,   //Node G 6
        0., -2., -1.,   //Node H 7 
        2., -1., -1.,   //Node I 8
       -2., -1., -1.,   //Node J 9

    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{
        {0, 1, 4},  //Face ABE 1
        {0, 1, 3},  //Face ABD 2
        {0, 3, 2},  //Face ADC 3
        {1, 2, 3},  //Face BCD 4
        {1, 4, 5},  //Face BEF 5
        {0, 4, 5},  //Face AEF 6

        {2, 6, 8},  //Face AGI 7
        {0, 6, 2},  //Face ACI 8
        {2, 8, 7},  //Face BHI 9
        {1, 2, 7},  //Face BCI 10

        {5, 9, 6},  //Face AFJ 11
        {0, 5, 6},  //Face AGJ 12
        {1, 7, 5},  //Face BHJ 13
        {5, 7, 9},  //Face BFJ 14

        {6, 7, 8},  //Face GHI 14
        {6, 7, 9}   //Face GHJ 14
    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;

    //Write the created mesh to check it
    mesh_writer::write_cell_data_file(std::string("./test_1.vtk"), {m});

    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();

    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge& edge_ab = const_cast<edge&>(*edge_it);

    bool t1 = edge_ab.is_manifold() == true;

    //Create the local mesh refiner
    local_mesh_refiner lmr(0.1, 0.3);


    //Remove the face ABD ADC and BCD
    bool t2 = lmr.can_be_merged(edge_ab, c) == false;
    bool t3 = c->get_mesh_revision() == 0;


    std::cout << t1 << std::endl;
    std::cout << t2 << std::endl;
    std::cout << t3 << std::endl;
 
    return !(t1 && t2 && t3);
}




/*
int local_mesh_refiner_tester::prepare_merger_test_1(){
    
//          A
//       / /|\ ＼     
//     /  / | \  ＼    
//   /  6/  |  \ 3 ＼  
//  F__E/ 1 | 2 \D__＼C
//  \   \   |   /   ／
//    \5 \  |  / 4／  
//      \ \ | / ／    
//       \ \|/／      
//          B
//   


   //Create the geometry shown above

    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,   //Node A 0
        0., -2., 0.,   //Node B 1 
        2., -1., 0.,   //Node C 2
        1., -1., 0.,   //Node D 3
       -1., -1., 0.,   //Node E 4
       -2., -1., 0.,   //Node F 5

        0.,  0., -1.,   //Node G 6
        0., -2., -1.,   //Node H 7 
        2., -1., -1.,   //Node I 8
       -2., -1., -1.,   //Node J 9

    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{
        {0, 1, 4},  //Face ABE 1
        {0, 1, 3},  //Face ABD 2
        {0, 3, 2},  //Face ADC 3
        {1, 2, 3},  //Face BCD 4
        {1, 4, 5},  //Face BEF 5
        {0, 4, 5},  //Face AEF 6

        {2, 6, 8},  //Face AGI 7
        {0, 6, 2},  //Face ACI 8
        {2, 8, 7},  //Face BHI 9
        {1, 2, 7},  //Face BCI 10

        {5, 9, 6},  //Face AFJ 11
        {0, 5, 6},  //Face AGJ 12
        {1, 7, 5},  //Face BHJ 13
        {5, 7, 9},  //Face BFJ 14

        {6, 7, 8},  //Face GHI 14
        {6, 7, 9}   //Face GHJ 14
    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;

    //Write the created mesh to check it
    mesh_writer::write_cell_data_file(std::string("./test_1.vtk"), {m});

    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();

    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge& edge_ab = const_cast<edge&>(*edge_it);

    bool t1 = edge_ab.is_manifold() == true;

    //Create the local mesh refiner
    local_mesh_refiner lmr(0.1, 0.3);

    edge_set dummy_set;

    //Remove the face ABD ADC and BCD
    lmr.prepare_merger(edge_ab, c, dummy_set);
 
    bool t2 = c->free_face_queue_.size() == 4;

    //Get the 2 faces that should be left
    const face& f1 = c->get_face_lst()[edge_it->f1()];
    const face& f2 = c->get_face_lst()[edge_it->f2()];

    //Make sure the 2 faces are made of the correct nodes
    std::array<unsigned, 3> f1_nodes = f1.get_node_ids();
    std::array<unsigned, 3> f2_nodes = f2.get_node_ids();

    //Sort the nodes 
    std::sort(f1_nodes.begin(), f1_nodes.end());
    std::sort(f2_nodes.begin(), f2_nodes.end());

    print_container(f1_nodes);
    print_container(f2_nodes);

    bool t3 = (
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{0, 1, 2}.begin()) ||
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{0, 1, 5}.begin())
            );
    bool t4 = (
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{0, 1, 2}.begin()) ||
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{0, 1, 5}.begin())
            );

    //Write the result in a vtk file
    mesh_writer::write_cell_data_file(std::string("./test_2.vtk"), {c});

    std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;
    std::cout << "t3 " << t3 << std::endl;
    std::cout << "t4 " << t4 << std::endl;

    return !(t1 && t2 && t3 && t4);
}




int local_mesh_refiner_tester::prepare_merger_test_2(){
//   
//          A
//       / /|\ ＼     
//     /  / | \  ＼    
//   /  6/  |  \ 3 ＼  
//  F__E/ 1 | 2 \D__＼C
//  \   \   |   /   ／
//    \5 \  |  / 4／  
//      \ \ | / ／    
//       \ \|/／      
//          B
//   

   //Create the geometry shown above

    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,   //Node A 0
        0., -2., 0.,   //Node B 1 
        2., -1., 0.,   //Node C 2
        1., -1., 0.,   //Node D 3
       -1., -1., 0.,   //Node E 4
       -2., -1., 0.,   //Node F 5

        0.,  0., -1.,   //Node G 6
        0., -2., -1.,   //Node H 7 
        2., -1., -1.,   //Node I 8
       -2., -1., -1.,   //Node J 9

       -1.5, -1., 0.,   //Node K 10
        1.5, -1., 0.,   //Node L 11


    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{
        {0, 1, 4},  //Face ABE 1
        {0, 1, 3},  //Face ABD 2

        {0, 11, 2},  //Face ALC 3
        {1, 2, 11},  //Face BCL 4
        {0, 3, 11},  //Face ADL 3
        {1, 11, 3},  //Face BLD 4

        {1, 10, 5},  //Face BEF 5
        {0, 10, 5},  //Face AEF 6
        {0, 4, 10},  //Face AEK 6
        {1, 4, 10},  //Face BEK 6


        {2, 6, 8},  //Face AGI 7
        {0, 6, 2},  //Face ACI 8
        {2, 8, 7},  //Face BHI 9
        {1, 2, 7},  //Face BCI 10

        {5, 9, 6},  //Face AFJ 11
        {0, 5, 6},  //Face AGJ 12
        {1, 7, 5},  //Face BHJ 13
        {5, 7, 9},  //Face BFJ 14

        {6, 7, 8},  //Face GHI 14
        {6, 7, 9}   //Face GHJ 14
    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;

    //Write the created mesh to check it
    mesh_writer::write_cell_data_file(std::string("./test_3.vtk"), {m});

    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();

    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge& edge_ab = const_cast<edge&>(*edge_it);

    bool t1 = edge_ab.is_manifold() == true;

    //Create the local mesh refiner
    local_mesh_refiner lmr(0.1, 0.3);

    edge_set dummy_set;

    //Remove the face ABD ADC and BCD
    lmr.prepare_merger(edge_ab, c, dummy_set);
 
    bool t2 = c->free_face_queue_.size() == 8;

    //Get the 2 faces that should be left
    const face& f1 = c->get_face_lst()[edge_it->f1()];
    const face& f2 = c->get_face_lst()[edge_it->f2()];

    //Make sure the 2 faces are made of the correct nodes
    std::array<unsigned, 3> f1_nodes = f1.get_node_ids();
    std::array<unsigned, 3> f2_nodes = f2.get_node_ids();

    //Sort the nodes 
    std::sort(f1_nodes.begin(), f1_nodes.end());
    std::sort(f2_nodes.begin(), f2_nodes.end());

    print_container(f1_nodes);
    print_container(f2_nodes);

    bool t3 = (
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{0, 1, 2}.begin()) ||
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{0, 1, 5}.begin())
            );
    bool t4 = (
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{0, 1, 2}.begin()) ||
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{0, 1, 5}.begin())
            );

    //Write the result in a vtk file
    mesh_writer::write_cell_data_file(std::string("./test_4.vtk"), {c});

    std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;
    std::cout << "t3 " << t3 << std::endl;
    std::cout << "t4 " << t4 << std::endl;

    return !(t1 && t2 && t3 && t4);
}
//---------------------------------------------------------------------------------------------------------
*/

//---------------------------------------------------------------------------------------------------------
int local_mesh_refiner_tester::edge_swap_test(){


    /*
            A
           /|\     
          / | \     
         /  |  \   
       C/ 1 | 2 \D
        \   |   /   
         \  |  /   
          \ | /     
           \|/      
            B
    */

   //Create the geometry shown above

    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,    //Node A 0
        0., -3., 0.,    //Node B 1 
       -1., -1.5, 0.,   //Node C 2
        1., -1.5, 0.,   //Node D 3

        0.,  0.,  -1.,   //Node E 4
        0., -3.,  -1.,   //Node F 5 
       -1., -1.5, -1.,   //Node G 6
        1., -1.5, -1.,   //Node H 7
    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{
        {0, 1, 2},  //Face ABC 
        {0, 1, 3},   //Face ABD 
        {0, 4, 2},   //Face AEC 
        {2, 6, 4},   //Face CGE 
        {2, 6, 5},   //Face CGF 
        {5, 1, 2},    //Face FBC
        {0, 3, 7},    //Face ADH
        {7, 4, 0},    //Face HEA
        {3, 1, 5},    //Face DBF
        {5, 7, 3},    //Face FHD
        {4, 5, 6},    //Face EFG
        {4, 5, 7},    //Face EFH

    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;

    //Write the created mesh to check it
    mesh_writer::write_cell_data_file(std::string("./test_5.vtk"), {m});

    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();

    
    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge& edge_ab = const_cast<edge&>(*edge_it);

    //Create the local mesh refiner
    auto event_sink = std::make_shared<recording_remesh_sink>();
    local_mesh_refiner lmr(0.1, 0.3, true, event_sink);

    //Remove the face ABD ADC and BCD
    lmr.swap_edge(edge_ab, c);

    mesh_writer::write_cell_data_file(std::string("./test_6.vtk"), {c});

    bool t1 = c->edge_set_.find(edge(0, 1)) == c->edge_set_.end();

    auto edge_it2 = c->edge_set_.find(edge(2, 3));

    if(edge_it2 == c->edge_set_.end()){
        std::cout << "edge cd not found" << std::endl;
        return 1;
    }

    const edge& edge_cd = *(edge_it2);

    const face& f1 = c->get_face_lst()[edge_cd.f1()];
    const face& f2 = c->get_face_lst()[edge_cd.f2()];

    //Make sure the 2 faces are made of the correct nodes
    std::array<unsigned, 3> f1_nodes = f1.get_node_ids();
    std::array<unsigned, 3> f2_nodes = f2.get_node_ids();

    //Sort the nodes
    std::sort(f1_nodes.begin(), f1_nodes.end());
    std::sort(f2_nodes.begin(), f2_nodes.end());

    bool t2 = (
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{0, 2, 3}.begin()) ||
                std::equal(f1_nodes.begin(), f1_nodes.end(), std::vector<unsigned int>{1, 2, 3}.begin())
            );

    bool t3 = (
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{0, 2, 3}.begin()) ||
                std::equal(f2_nodes.begin(), f2_nodes.end(), std::vector<unsigned int>{1, 2, 3}.begin())
            );

    bool t4 = false;
    if(event_sink->records.size() == 1){
        const auto& record = event_sink->records.front();
        t4 = (
            record.event.operation == prl::core::RemeshOperation::edge_swap
            && prl::core::is_valid_remesh_event(record.event, record.before, record.after)
            && record.event.cell_id == c->get_id()
            && record.event.before_revision == 0
            && record.event.after_revision == 1
            && record.before.vertices.size() == record.after.vertices.size()
            && record.before.faces.size() == record.after.faces.size()
            && sorted_vertex_ids(record.before) == sorted_vertex_ids(record.after)
        );
    }

    bool t5 = false;
    const auto reverse_edge_it = c->get_edge_set().find(edge(2, 3));
    if(reverse_edge_it != c->get_edge_set().end()){
        local_mesh_refiner legacy_lmr(0.1, 0.3);
        legacy_lmr.swap_edge(const_cast<edge&>(*reverse_edge_it), c);
        t5 = c->get_mesh_revision() == 2 && event_sink->records.size() == 1;
    }

    std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;
    std::cout << "t3 " << t3 << std::endl;
    std::cout << "t4 " << t4 << std::endl;
    std::cout << "t5 " << t5 << std::endl;

    return !(t1 && t2 && t3 && t4 && t5);


}
//---------------------------------------------------------------------------------------------------------

//---------------------------------------------------------------------------------------------------------
int local_mesh_refiner_tester::split_edge_test(){
    /*

    Start by recreating the geometry shown below

       E____C___F
       |   /\   |  
       |  /  \  |   
       | /    \ |  
       A/______\B
       |\      /|   
       | \    / |  
       |  \  /  |   
       |___\/___|   
       H   D    G
    */


    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,    //Node A 0
        1.,  0., 0.,    //Node B 1
        0.5, 1., 0.,    //Node C 2
        0.5, -1., 0.,   //Node D 3
        0.,  1.,  0.,   //Node E 4      
        1.,  1.,  0.,   //Node F 5
        1., -1., 0.,    //Node G 6
        0., -1., 0.,    //Node H 7


        0.,  0., -1.,    //Node I 8
        1.,  0., -1.,    //Node J 9
        0.5, 1., -1.,    //Node K 10
        0.5, -1., -1.,   //Node L 11
        0.,  1.,  -1.,   //Node M 12      
        1.,  1.,  -1.,   //Node N 13
        1., -1., -1.,    //Node O 14
        0., -1., -1.,    //Node P 15
    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{

        //The top 
        {0, 1, 2},  //Face ABC 0
        {0, 1, 3},  //Face ABD 1
        {0, 2, 4},  //Face ACE 2
        {1, 2, 5},  //Face BCF 3
        {0, 3, 7},  //Face ADH 4
        {1, 6, 3},  //Face BGD 5

        //The bottom
        {8, 9, 10},  //Face IJK 6
        {8, 9, 11},  //Face IJL 7
        {8, 10, 12},  //Face IKM 8
        {9, 10, 13},  //Face JKN 9
        {8, 11, 15},  //Face IPL 10
        {9, 14, 11},  //Face JLO 11

        //The sides
        {0, 8, 4 }, // Face AIE 
        {4, 12, 8}, // Face EMI
        {0, 8, 15}, // Face AIP
        {15, 7, 0}, // Face PHA

        {1, 9, 5 }, // Face BJF 
        {5, 13, 9}, // Face FNJ
        {1, 9, 14}, // Face BJO
        {14, 6, 1}, // Face OGB

        {4, 2, 10 }, // Face ECK
        {10, 12, 4}, // Face KME
        {5, 2, 10 }, // Face FCK
        {10, 13, 5}, // Face KNF

        {7, 3, 11 }, // Face HDL
        {11, 15, 7}, // Face LPH
        {6, 3, 11 }, // Face GDL
        {11, 14, 6}, // Face LOG

    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;

    //Write the created mesh to check it
    mesh_writer::write_cell_data_file(std::string("./test_7.vtk"), {m});


    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();


    #if DYNAMIC_MODEL_INDEX == 0
    //Add somee momentum to the nodes 0 and 1
    c->node_lst_[0].set_momentum(vec3(0, 0, 1));
    c->node_lst_[1].set_momentum(vec3(0, 0, 1));
    #endif


    const unsigned nb_edge_before = c->get_edge_set().size();
    const unsigned nb_node_before = c->get_node_lst().size();
    const unsigned nb_face_before = c->get_face_lst().size();

    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge& edge_ab = const_cast<edge&>(*edge_it);

    //Create the local mesh refiner
    auto event_sink = std::make_shared<recording_remesh_sink>();
    local_mesh_refiner lmr(0.1, 0.3, true, event_sink);

    edge_set dummy_set;

    //Remove the face ABD ADC and BCD
    lmr.split_edge(edge_ab, c, dummy_set);

    mesh_writer::write_cell_data_file(std::string("./test_8.vtk"), {c});

    //Check that the new edges have been added to the edge to check
    bool t1 = dummy_set.size() == 4;

    //Make sure the number of edges in the cell has increased by 3
    bool t2 = c->get_edge_set().size() == nb_edge_before + 3;

    unsigned nb_node_after = std::count_if(c->get_node_lst().begin(), c->get_node_lst().end(), [](const node& n){return n.is_used();});
    unsigned nb_face_after = std::count_if(c->get_face_lst().begin(), c->get_face_lst().end(), [](const face& f){return f.is_used();});

    bool t3 = nb_node_after == nb_node_before + 1;
    bool t4 = nb_face_after == nb_face_before + 2;
 
    //Make sure all the edges of the cell are connected to 2 faces
    bool t5 = c->is_manifold();

    //Make sure no momentum has been lost
    #if DYNAMIC_MODEL_INDEX == 0
        const vec3 total_momentum = std::accumulate(
            c->get_node_lst().begin(), 
            c->get_node_lst().end(), 
            vec3(0, 0, 0), 
            [](const vec3& a, const node& b){return a + b.momentum();}
        );
        bool t6 = total_momentum == vec3(0, 0, 2);
    #else
        bool t6 = true;
    #endif

    bool t7 = false;
    if(event_sink->records.size() == 1){
        const auto& record = event_sink->records.front();
        const auto before_ids = sorted_vertex_ids(record.before);
        const auto after_ids = sorted_vertex_ids(record.after);
        t7 = (
            record.event.operation == prl::core::RemeshOperation::edge_split
            && prl::core::is_valid_remesh_event(record.event, record.before, record.after)
            && record.event.before_revision == 0
            && record.event.after_revision == 1
            && record.after.vertices.size() == record.before.vertices.size() + 1
            && record.after.faces.size() == record.before.faces.size() + 2
            && std::includes(after_ids.begin(), after_ids.end(), before_ids.begin(), before_ids.end())
        );
    }
    

    std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;
    std::cout << "t3 " << t3 << std::endl;
    std::cout << "t4 " << t4 << std::endl;
    std::cout << "t5 " << t5 << std::endl;
    std::cout << "t6 " << t6 << std::endl;
    std::cout << "t7 " << t7 << std::endl;

    return !(t1 && t2 && t3 && t4 && t5 && t6 && t7);
}
//---------------------------------------------------------------------------------------------------------



//---------------------------------------------------------------------------------------------------------
int local_mesh_refiner_tester::merge_edge_test(){
    /*

    Start by recreating the geometry shown below

       E____C___F
       |   /\   |  
       |  /  \  |   
       | /    \ |  
       A/______\B
       |\      /|   
       | \    / |  
       |  \  /  |   
       |___\/___|   
       H   D    G
    */


    //Create the nodes
    std::vector<double> node_pos_lst{
        0.,  0., 0.,    //Node A 0
        1.,  0., 0.,    //Node B 1
        0.5, 1., 0.,    //Node C 2
        0.5, -1., 0.,   //Node D 3
        0.,  1.,  0.,   //Node E 4      
        1.,  1.,  0.,   //Node F 5
        1., -1., 0.,    //Node G 6
        0., -1., 0.,    //Node H 7


        0.,  0., -1.,    //Node I 8
        1.,  0., -1.,    //Node J 9
        0.5, 1., -1.,    //Node K 10
        0.5, -1., -1.,   //Node L 11
        0.,  1.,  -1.,   //Node M 12      
        1.,  1.,  -1.,   //Node N 13
        1., -1., -1.,    //Node O 14
        0., -1., -1.,    //Node P 15
    };

    //Create the faces
    std::vector<std::vector<unsigned>> face_conn_lst{

        //The top 
        {0, 1, 2},  //Face ABC 0
        {0, 1, 3},  //Face ABD 1
        {0, 2, 4},  //Face ACE 2
        {1, 2, 5},  //Face BCF 3
        {0, 3, 7},  //Face ADH 4
        {1, 6, 3},  //Face BGD 5

        //The bottom
        {8, 9, 10},  //Face IJK 6
        {8, 9, 11},  //Face IJL 7
        {8, 10, 12},  //Face IKM 8
        {9, 10, 13},  //Face JKN 9
        {8, 11, 15},  //Face IPL 10
        {9, 14, 11},  //Face JLO 11

        //The sides
        {0, 8, 4 }, // Face AIE 
        {4, 12, 8}, // Face EMI
        {0, 8, 15}, // Face AIP
        {15, 7, 0}, // Face PHA

        {1, 9, 5 }, // Face BJF 
        {5, 13, 9}, // Face FNJ
        {1, 9, 14}, // Face BJO
        {14, 6, 1}, // Face OGB

        {4, 2, 10 }, // Face ECK
        {10, 12, 4}, // Face KME
        {5, 2, 10 }, // Face FCK
        {10, 13, 5}, // Face KNF

        {7, 3, 11 }, // Face HDL
        {11, 15, 7}, // Face LPH
        {6, 3, 11 }, // Face GDL
        {11, 14, 6}, // Face LOG

    };

    mesh m;
    m.node_pos_lst = node_pos_lst;
    m.face_point_ids = face_conn_lst;


    //Transform the mesh into a cell
    cell_ptr c = std::make_shared<cell>(m, 0);
    c->generate_edge_set();


    #if DYNAMIC_MODEL_INDEX == 0
    //Add somee momentum to the nodes 0 and 1
    c->node_lst_[0].set_momentum(vec3(0, 0, 1));
    c->node_lst_[1].set_momentum(vec3(0, 0, 1));
    #endif

    const unsigned nb_edge_before = c->get_edge_set().size();
    const unsigned nb_node_before = c->get_node_lst().size();
    const unsigned nb_face_before = c->get_face_lst().size();

    //Get the edge AB
    auto edge_it = c->get_edge_set().find(edge(0, 1));

    if(edge_it == c->get_edge_set().end()){
        std::cout << "edge ab not found" << std::endl;
        return 1;
    }
    
    edge edge_ab = const_cast<edge&>(*edge_it);


    //Create the local mesh refiner
    auto event_sink = std::make_shared<recording_remesh_sink>();
    local_mesh_refiner lmr(0.1, 0.3, true, event_sink);


    edge_set dummy_set;

    //Remove the face ABD ADC and BCD
    lmr.merge_edge(edge_ab, c, dummy_set);

    //Get the ids of the inserted edge
    unsigned new_node_id = c->get_node_lst().size() - 1;

    //Count the number of edges in which the new node is involved
    unsigned nb_edge_with_new_node = std::count_if(
        c->edge_set_.begin(),
        c->edge_set_.end(),
        [new_node_id](const edge& e){
            return e.n1() == new_node_id || e.n2() == new_node_id;
        }
    );


    //Check that the new edges have been added to the edge to check
    bool t1 = dummy_set.size() == nb_edge_with_new_node;

    //Make sure the number of edges in the cell has increased by 3
    bool t2 = c->get_edge_set().size() == nb_edge_before - 3;

    unsigned nb_node_after = std::count_if(c->get_node_lst().begin(), c->get_node_lst().end(), [](const node& n){return n.is_used();});
    unsigned nb_face_after = std::count_if(c->get_face_lst().begin(), c->get_face_lst().end(), [](const face& f){return f.is_used();});

    bool t3 = nb_node_after == nb_node_before - 1;
    bool t4 = nb_face_after == nb_face_before - 2;
 
    //Make sure all the edges of the cell are connected to 2 faces
    const auto& edge_set = c->get_edge_set();

    bool t5 = std::all_of(edge_set.begin(), edge_set.end(), [](const edge& e) -> bool{return e.is_manifold();});

    #if DYNAMIC_MODEL_INDEX == 0

    //Make sure no momentum has been lost
    const vec3 total_momentum = std::accumulate(
        c->get_node_lst().begin(), 
        c->get_node_lst().end(), 
        vec3(0, 0, 0), 
        [](const vec3& a, const node& b){return a + b.momentum();}
    );
    
        bool t6 = total_momentum == vec3(0, 0, 2);
    #else 
        bool t6 = true;
    #endif



    //Make sure that the 2 merged nodes are not part of any edge
    bool t7 = std::all_of(
        c->edge_set_.begin(),
        c->edge_set_.end(),
        [&edge_ab](const edge& e){
            return e.n1() != edge_ab.n1() && e.n2() != edge_ab.n1() && e.n1() != edge_ab.n2() && e.n2() != edge_ab.n2();
        }
    );

    //Make sure that the 2 merged faces are not part of any edge
    bool t8 = std::all_of(
        c->edge_set_.begin(),
        c->edge_set_.end(),
        [&edge_ab](const edge& e){
            return e.f1() != edge_ab.f1() && e.f2() != edge_ab.f1() && e.f1() != edge_ab.f2() && e.f2() != edge_ab.f2();
        }
    );

    //Make sure that no edge in the cell has the same nodes
    bool t9 = std::all_of(
        c->edge_set_.begin(),
        c->edge_set_.end(),
        [](const edge& e){
            return e.n1() != e.n2();
        }
    );

    bool t10 = false;
    if(event_sink->records.size() == 1){
        const auto& record = event_sink->records.front();
        const auto before_ids = sorted_vertex_ids(record.before);
        const auto after_ids = sorted_vertex_ids(record.after);
        std::vector<std::uint64_t> retained_ids;
        std::set_intersection(
            before_ids.begin(), before_ids.end(),
            after_ids.begin(), after_ids.end(),
            std::back_inserter(retained_ids)
        );
        t10 = (
            record.event.operation == prl::core::RemeshOperation::edge_merge
            && prl::core::is_valid_remesh_event(record.event, record.before, record.after)
            && record.event.before_revision == 0
            && record.event.after_revision == 1
            && record.after.vertices.size() + 1 == record.before.vertices.size()
            && record.after.faces.size() + 2 == record.before.faces.size()
            && retained_ids.size() + 1 == record.after.vertices.size()
        );
    }

    const auto before_rebase = lmr.capture_surface_snapshot(*c);
    c->rebase();
    const auto after_rebase = lmr.capture_surface_snapshot(*c);
    const auto before_rebase_ids = sorted_vertex_ids(before_rebase);
    const auto after_rebase_ids = sorted_vertex_ids(after_rebase);
    const bool t11 = (
        before_rebase_ids == after_rebase_ids
        && std::adjacent_find(after_rebase_ids.begin(), after_rebase_ids.end()) == after_rebase_ids.end()
    );



    mesh_writer::write_cell_data_file(std::string("./test_9.vtk"), {c});



    //std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;
    std::cout << "t3 " << t3 << std::endl;
    std::cout << "t4 " << t4 << std::endl;
    std::cout << "t5 " << t5 << std::endl;
    std::cout << "t6 " << t6 << std::endl;
    std::cout << "t7 " << t7 << std::endl;
    std::cout << "t8 " << t8 << std::endl;
    std::cout << "t9 " << t9 << std::endl;
    std::cout << "t10 " << t10 << std::endl;
    std::cout << "t11 " << t11 << std::endl;

    return !(t1 && t2 && t3 && t4 && t5 && t6 && t7 && t8 && t9 && t10 && t11);
}
//---------------------------------------------------------------------------------------------------------





//---------------------------------------------------------------------------------------------------------
int local_mesh_refiner_tester::get_triangle_score_test(){
    


    std::vector<double> cell_node_pos_lst{
        1,0,0,  0,1,0,  0,0,1, 
        0,0,0,  1,0,0,  0.5, 0.1,0, 
    };



    std::vector<unsigned> cell_face_connectivity{0, 1, 2, 3, 4, 5};
    cell_ptr c = std::make_shared<cell>(cell_node_pos_lst, cell_face_connectivity, 0);
    c->generate_edge_set();
    c->update_all_face_normals_and_areas();


    face& f1 = const_cast<face&>(c->get_face_lst()[0]);
    face& f2 = const_cast<face&>(c->get_face_lst()[1]);

    //Create the local mesh refiner
    local_mesh_refiner lmr(0.1, 0.3);

    //Get the score of the triangle
    auto [score, longest_edge] = lmr.get_triangle_score(c, f1);

    bool t1 = almost_equal(score, 1.);

    auto [score_2, longest_edge_2] = lmr.get_triangle_score(c, f2);
    bool t2 = longest_edge_2.n1() == 3 && longest_edge_2.n2() == 4;

    std::cout << score_2 << std::endl;

    std::cout << "t1 " << t1 << std::endl;
    std::cout << "t2 " << t2 << std::endl;

    return !(t1 && t2);
}
//---------------------------------------------------------------------------------------------------------





//---------------------------------------------------------------------------------------------------------
// The main function
int main (int argc, char** argv){

    //Check that the command line input is correctly formatted
    assert(argc == 2); 

    //Get the name of the test to run
    std::string test_name = argv[1];

    local_mesh_refiner_tester tester;
    
    //Run the selected test

    if (test_name == "can_be_merged_test")             return tester.can_be_merged_test();

    //if (test_name == "prepare_merger_test_1")         return tester.prepare_merger_test_1();
    //if (test_name == "prepare_merger_test_2")         return tester.prepare_merger_test_2();
    if (test_name == "edge_swap_test")                return tester.edge_swap_test();
    if (test_name == "split_edge_test")               return tester.split_edge_test();
    if (test_name == "merge_edge_test")               return tester.merge_edge_test();
    if (test_name == "get_triangle_score_test")       return tester.get_triangle_score_test();

    
    

    std::cout << "TEST NAME: " << test_name << " DOES NOT EXIST" << std::endl;
    return 1;
}
//---------------------------------------------------------------------------------------------------------

