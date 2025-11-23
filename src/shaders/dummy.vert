#version 330 core

// 1. Input: The position of the vertex from the VBO (Full-Screen Quad data)
in vec2 in_vert;

// 2. Output: The UV coordinate (normalized coordinates) to be passed to the Fragment Shader
out vec2 frag_uv;

void main() {
    // Set the final clip-space position of the vertex
    // The VBO positions are usually already in Normalized Device Coordinates (-1.0 to 1.0)
    gl_Position = vec4(in_vert, 0.0, 1.0);
    
    // Pass the UV coordinate to the fragment shader
    // A common trick is to transform [-1, 1] to [0, 1] for the UV:
    vec2 mapped_uv = in_vert * 0.5 + 0.5;

    // 2. Flip the Y component:
    // If mapped_uv.y is 0.0 (bottom), 1.0 - 0.0 = 1.0 (top of image)
    // If mapped_uv.y is 1.0 (top), 1.0 - 1.0 = 0.0 (bottom of image)
    frag_uv = vec2(mapped_uv.x, 1.0 - mapped_uv.y);
}