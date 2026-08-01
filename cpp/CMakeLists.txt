cmake_minimum_required(VERSION 3.16)
project(prl_core LANGUAGES CXX)

include(CTest)

add_library(prl_core INTERFACE)
target_compile_features(prl_core INTERFACE cxx_std_17)
target_include_directories(
    prl_core
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

if(BUILD_TESTING)
    add_executable(prl_remesh_contract_test tests/remesh_contract_test.cpp)
    target_link_libraries(prl_remesh_contract_test PRIVATE prl_core)
    add_test(NAME prl_remesh_contract_test COMMAND prl_remesh_contract_test)
endif()
