#pragma once
#include "contact_model_abstract.hpp"
#include <limits>
#include <stdexcept>

// Geometric safety, not an elastic reference state or an extra force law.
namespace prl { namespace contact_safety {
using Triangle=std::array<vec3,3>;
inline double segment_distance(const vec3& a,const vec3& b,const vec3& c,const vec3& d){
    const vec3 u=b-a,v=d-c,w=a-c;
    const double aa=u.dot(u),bb=u.dot(v),cc=v.dot(v),dd=u.dot(w),ee=v.dot(w),den=aa*cc-bb*bb;
    if(!(aa>1e-24 && cc>1e-24))throw std::runtime_error("degenerate segment");
    const auto clamp=[](double x){return std::max(0.,std::min(1.,x));};
    double s=den>1e-14*aa*cc?clamp((bb*ee-cc*dd)/den):0.;
    double t=(bb*s+ee)/cc;
    if(t<0.){t=0.;s=clamp(-dd/aa);}else if(t>1.){t=1.;s=clamp((bb-dd)/aa);}
    return (w+u*s-v*t).norm();
}
inline bool segment_hits(const vec3& p,const vec3& q,const Triangle& t){
    const vec3 direction=q-p,e=t[1]-t[0],f=t[2]-t[0],h=direction.cross(f);
    const double det=e.dot(h),scale=e.norm()*f.norm()*direction.norm();
    if(std::abs(det)<=1e-12*scale)return false; // coplanarity handled by distances
    const vec3 s=p-t[0],cross=s.cross(e);const double u=s.dot(h)/det,v=direction.dot(cross)/det,alpha=f.dot(cross)/det;
    return u>=-1e-12 && v>=-1e-12 && u+v<=1.+1e-12 && alpha>=-1e-12 && alpha<=1.+1e-12;
}
inline double triangle_distance(const Triangle& a,const Triangle& b){
    double result=std::numeric_limits<double>::infinity();
    for(unsigned i=0;i<3;++i){
        if(segment_hits(a[i],a[(i+1)%3],b)||segment_hits(b[i],b[(i+1)%3],a))return 0.;
        result=std::min(result,std::sqrt(std::max(0.,contact_model_abstract::compute_node_triangle_distance(a[i],b[0],b[1],b[2]).first)));
        result=std::min(result,std::sqrt(std::max(0.,contact_model_abstract::compute_node_triangle_distance(b[i],a[0],a[1],a[2]).first)));
        for(unsigned j=0;j<3;++j)result=std::min(result,segment_distance(a[i],a[(i+1)%3],b[j],b[(j+1)%3]));
    }return result;
}
struct Separation {double intercell=1e30,nonincident=1e30,min_height=1e30;};
inline Separation measure(const std::vector<cell_ptr>& cells){
    struct Facet {Triangle p;std::array<unsigned,3> ids;unsigned cell;std::array<double,3> low,high;};
    std::vector<Facet> facets;Separation result;
    for(unsigned cid=0;cid<cells.size();++cid)for(const auto& f:cells[cid]->get_face_lst())if(f.is_used()){
        Facet entry;entry.cell=cid;entry.ids=f.get_node_ids();
        for(unsigned i=0;i<3;++i)entry.p[i]=cells[cid]->get_node_lst()[entry.ids[i]].pos();
        const double longest=std::max({(entry.p[1]-entry.p[0]).norm(),(entry.p[2]-entry.p[1]).norm(),(entry.p[0]-entry.p[2]).norm()});
        result.min_height=std::min(result.min_height,(entry.p[1]-entry.p[0]).cross(entry.p[2]-entry.p[0]).norm()/longest);
        const auto xyz=[](const vec3& p){return std::array<double,3>{p.dx(),p.dy(),p.dz()};};
        for(unsigned k=0;k<3;++k){entry.low[k]=std::min({xyz(entry.p[0])[k],xyz(entry.p[1])[k],xyz(entry.p[2])[k]});entry.high[k]=std::max({xyz(entry.p[0])[k],xyz(entry.p[1])[k],xyz(entry.p[2])[k]});}
        facets.push_back(entry);
    }
    for(size_t i=0;i<facets.size();++i)for(size_t j=i+1;j<facets.size();++j){
        const auto& a=facets[i];const auto& b=facets[j];const bool same=a.cell==b.cell;
        if(same){bool shared=false;for(auto u:a.ids)for(auto v:b.ids)shared=shared||u==v;if(shared)continue;}
        double& best=same?result.nonincident:result.intercell;double lower=0.;
        for(unsigned k=0;k<3;++k){const double gap=std::max({a.low[k]-b.high[k],b.low[k]-a.high[k],0.});lower+=gap*gap;}
        if(lower>=best*best)continue;
        best=std::min(best,triangle_distance(a.p,b.p));
    }return result;
}
inline double safe_increment(const Separation& geometry,double maximum_speed,double requested){
    const double distance=std::min(geometry.intercell,geometry.nonincident);
    if(!(distance>1e-8) || !(geometry.min_height>1e-8))throw std::runtime_error("surface separation/height safety floor");
    if(maximum_speed==0.)return requested;
    // A moving triangle stays within vmax*dt of its old position. Two triangles
    // cannot close dmin when 2*vmax*dt <= .8*(dmin-roundoff margin).
    return std::min({requested,.4*(distance-1e-10)/maximum_speed,.05*geometry.min_height/maximum_speed});
}
}}
