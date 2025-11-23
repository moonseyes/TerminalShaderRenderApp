#version 330 core

precision lowp float;

// Input: The UV coordinate from the Vertex Shader
in vec2 frag_uv;

uniform float iTime;
uniform vec2 iResolution;

const float NUMBER_OF_STEPS = 128.0;
const float MIN_DIST_TO_TRAVEL = 0.001;
const float MAX_DIST_TO_TRAVEL = 64.0;

// Output: The final color
out vec4 out_color; // Standard ModernGL/OpenGL output name

float sdfSphere(vec3 p, vec3 c, float r) {
    return length(p - c) - r;
}

float sdfPlane( vec3 p, vec3 n, float h )
{
  // n must be normalized
  return dot(p,normalize(n)) + h;
}

float opSmoothUnion( float d1, float d2, float k ) {
    float h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0);
    return mix(d2, d1, h) - k * h * (1.0 - h);
}

float map(vec3 p) {
    float radius = 0.8;
    vec3 center = vec3(0.0);

    center = vec3(0.0, sin(iTime), 0.0);

    float sphere = sdfSphere(p, center, radius);
    
    // add plane
    float h = 1.0;
    vec3 normal = vec3(0.0, 1.0, 0.0);
    float plane = sdfPlane(p, normal, h);
    float m = opSmoothUnion(sphere, plane, 0.2);

    return m;
}

vec3 getNormal(vec3 p) {
    vec2 d = vec2(0.01, 0.0);
    float gx = map(p + d.xyy) - map(p - d.xyy);
    float gy = map(p + d.yxy) - map(p - d.yxy);
    float gz = map(p + d.yyx) - map(p - d.yyx);
    vec3 normal = vec3(gx, gy, gz);
    return normalize(normal);
}

float rayMarch(vec3 ro, vec3 rd, float maxDistToTravel) {
    float dist = 0.0;
    for (float i = 0.0; i < NUMBER_OF_STEPS; i++) {
        vec3 currentPos = ro + rd * dist;
        float distToSdf = map(currentPos);
        if (distToSdf < MIN_DIST_TO_TRAVEL) {
            break;
        }
        dist = dist + distToSdf;
        if (dist > maxDistToTravel) {
            break;
        }
    }
    return dist;
}

vec3 render(vec2 uv){
    vec3 color = vec3(0.0);
    vec3 ambient = vec3(0.5, 0.5, 0.5);

    vec3 ro = vec3(0.0, 0.0, -2);
    vec3 rd = vec3(uv, 1.0);
    float dist = rayMarch(ro, rd, MAX_DIST_TO_TRAVEL);

    if(dist < MAX_DIST_TO_TRAVEL){
        vec3 p = ro + rd * dist;
        vec3 normal = getNormal(p);
        vec3 lightColor = vec3(1.0, 0.94, 0.74);
        vec3 lightSource = vec3(2.0 * sin(2.0*iTime), 4.0, 2.0 * cos(iTime));
        float diffuseStrength = max(dot(normal, normalize(lightSource)), 0.0);
        vec3 diffuse = diffuseStrength * lightColor;

        vec3 viewSource = normalize(ro);
        vec3 reflectSource = normalize(reflect(-lightSource, normal));
        float specularStrength = pow(max(dot(viewSource, reflectSource), 0.0), 32.0);
        vec3 specular = specularStrength * lightColor;

        vec3 lighting = vec3(0.0, 0.0, 0.0);
        lighting = ambient * 0.1 + diffuse * 0.45 + specular * 0.45;
        color = lighting;

        // add shadow
        vec3 lightDirection = normalize(lightSource - p);
        float distToLightSource = length(lightSource - p);
        // check if the point is facing the light
        if (dot(normal, lightDirection) > 0.0){
            // check if the point is in shadow
            ro = p + normal * 0.1;
            rd = lightDirection;
            float dist = rayMarch(ro, rd, distToLightSource);
            if (dist < distToLightSource) {
                color = color * vec3(0.25);
            }
        }
        // add gamma correction
        color = pow(color, vec3(1.0/2.2));
    } else {
        color = vec3(uv.y/4+0.75) * vec3(0.5922, 0.7647, 0.8039);
    }
    return color;
}

void main() {
    // 1. Map the UV (0.0 to 1.0) to screen coordinates (0 to iResolution)
    vec2 uv = 2.0 * frag_uv - 1.0;
    uv.x = uv.x * (iResolution.x/iResolution.y);
    vec3 color = vec3(1.0);
    color = render(uv);
    // gl_FragColor = vec4(color, 1.0);
    out_color = vec4(color, 1.0);
}