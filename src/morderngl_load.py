import time
import os
from typing import Optional, Tuple

from PIL import Image
import moderngl as mgl
import numpy as np

# --- Configuration (can be passed to the class, but defined here for the example) ---
WIDTH, HEIGHT = 640, 480
FRAME_COUNT = 60 # Number of frames to render (not used in the current example, but useful for video)
FPS = 30.0
TIME_STEP = 1.0 / FPS
# ---------------------

class OffScreenRenderer:
    """
    A class to encapsulate ModernGL off-screen rendering resources and logic.
    It renders a full-screen quad using custom shaders into an FBO texture.
    """
    def __init__(self, width: int, height: int, vert_path: str, frag_path: str):
        """
        Initializes the ModernGL context, shader program, geometry, and FBO.
        """
        self.width = width
        self.height = height
        self.ctx: Optional[mgl.Context] = None
        self.program: Optional[mgl.Program] = None
        self.vao: Optional[mgl.VertexArray] = None
        self.fbo: Optional[mgl.Framebuffer] = None
        self.vbo: Optional[mgl.Buffer] = None
        self.ibo: Optional[mgl.Buffer] = None
        self.texture: Optional[mgl.Texture] = None
        self.i_time_uniform: Optional[mgl.Uniform] = None

        if not self._init_context():
            return
        
        if not self._init_shaders(vert_path, frag_path):
            self.release()
            return
            
        self._init_geometry()
        self._init_fbo()


    def _init_context(self) -> bool:
        """Sets up the ModernGL standalone context."""
        try:
            # 1. Setup Context (headless/standalone for off-screen rendering)
            self.ctx = mgl.create_standalone_context()
            print("ModernGL Context Created.")
            return True
        except Exception as e:
            print(f"Error creating ModernGL context: {e}")
            print("Ensure you have a suitable OpenGL driver or use a virtual screen (e.g., XVFB).")
            return False

    def _init_shaders(self, vert_path: str, frag_path: str) -> bool:
        """Loads and compiles the vertex and fragment shaders."""
        try:
            # Normalize path separators for different OS
            vert_path = vert_path.replace("\\","/")
            frag_path = frag_path.replace("\\","/")

            with open(vert_path, 'r') as f:
                vertex_shader = f.read()
            with open(frag_path, 'r') as f:
                fragment_shader = f.read()

            self.program = self.ctx.program(vertex_shader, fragment_shader)
            print("Shaders compiled successfully.")
        except Exception as e:
            print(f"Shader compilation error: {e}")
            return False

        # Get and set uniforms
        try:
            self.i_time_uniform = self.program['iTime']
            # Set iResolution once
            self.program['iResolution'].value = (self.width, self.height)
        except Exception as e:
            print(f"Error accessing uniform: {e}")
            # This is not critical for compilation, but necessary for the example
            pass 
        
        return True

    def _create_fullscreen_quad_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Creates vertex and index data for a full-screen quad."""
        # Positions are: X, Y
        quad_data = np.array([
            -1.0,  1.0,  # Top-Left
            -1.0, -1.0,  # Bottom-Left
             1.0,  1.0,  # Top-Right
             1.0, -1.0,  # Bottom-Right
        ], dtype='f4')

        # Indices to draw two triangles: 0, 1, 2 and 2, 1, 3
        indices = np.array([0, 1, 2,  2, 1, 3], dtype='i4')
        return quad_data, indices

    def _init_geometry(self):
        """Creates the VBO, IBO, and VAO for the full-screen quad."""
        # 3. Create Geometry (Full-Screen Quad)
        quad_data, indices = self._create_fullscreen_quad_data()
        self.vbo = self.ctx.buffer(quad_data.tobytes())
        self.ibo = self.ctx.buffer(indices.tobytes())

        # Create Vertex Array Object (VAO) to link the VBO to the 'in_vert' attribute
        # '2f' means two 4-byte floats (vec2)
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '2f', 'in_vert')], 
            self.ibo
        )
        print("VAO/VBO created.")

    def _init_fbo(self):
        """Creates the off-screen texture and Framebuffer Object (FBO)."""
        # 4. Create Texture and Framebuffer Object (FBO)
        # Texture for the GPU to render to (4 components/RGBA, 32-bit float per component)
        self.texture = self.ctx.texture((self.width, self.height), components=4, dtype='f4')
        
        # FBO is the off-screen rendering target
        self.fbo = self.ctx.framebuffer(color_attachments=[self.texture])
        self.fbo.use()
        print("FBO created.")

    def render_frame(self, current_time: float) -> Optional[np.ndarray]:
        """
        Renders a single frame at the given time using the initialized context.
        Returns the rendered frame as a (H, W, 4) numpy array with float values [0.0, 1.0].
        """
        if self.ctx is None or self.vao is None or self.fbo is None:
            print("Renderer not initialized successfully.")
            return None
        
        # Set the dynamic uniform value
        if self.i_time_uniform:
            self.i_time_uniform.value = current_time 
        
        # Use the FBO and set the viewport (optional, but good practice)
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.width, self.height)
        
        # Clear the FBO's color buffer
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        
        # Render the full-screen quad: this executes the fragment shader
        self.vao.render(mgl.TRIANGLES)
        
        # --- Read Back Data ---
        # Read 4-channel float data from the FBO texture
        # Must read from the currently bound FBO (which is self.fbo)
        raw_data = self.fbo.read(components=4, dtype='f4')
        
        # Convert raw buffer to NumPy array (H, W, 4)
        image_array = np.frombuffer(raw_data, dtype=np.float32).reshape(self.height, self.width, 4)
        
        return image_array

    def release(self):
        """
        Releases all ModernGL resources associated with the renderer.
        """
        if self.vbo: self.vbo.release()
        if self.ibo: self.ibo.release()
        if self.vao: self.vao.release()
        if self.texture: self.texture.release()
        if self.fbo: self.fbo.release()
        if self.program: self.program.release()
        # Note: The context itself is usually not explicitly released unless using certain backends
        # The GC will clean up the standalone context, but resource release is good practice.
        print("Render context resources released.")

    # Optional: Implement a context manager for guaranteed cleanup
    def __enter__(self):
        # Check if initialization was successful
        if self.ctx is None:
            raise RuntimeError("OffScreenRenderer failed to initialize.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

if __name__ == '__main__':
    # Ensure dummy shader files exist for the example to run.
    # The actual content of the shaders is not provided, but the paths are.
    DUMMY_VERT_PATH = "src/shaders/dummy.vert"
    RAYMARCHING_FRAG_PATH = "src/shaders/rayMarching.frag"
    
    # Simple check/creation of dummy files if they don't exist
    os.makedirs(os.path.dirname(DUMMY_VERT_PATH), exist_ok=True)
    if not os.path.exists(DUMMY_VERT_PATH):
        print(f"Creating dummy vertex shader at {DUMMY_VERT_PATH}")
        with open(DUMMY_VERT_PATH, 'w') as f:
            f.write("""
#version 330
in vec2 in_vert;
void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
""")
    if not os.path.exists(RAYMARCHING_FRAG_PATH):
        print(f"Creating dummy fragment shader at {RAYMARCHING_FRAG_PATH}")
        with open(RAYMARCHING_FRAG_PATH, 'w') as f:
            f.write("""
#version 330
uniform vec2 iResolution;
uniform float iTime;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution.xy;
    vec3 color = vec3(uv.x, uv.y, sin(iTime));
    fragColor = vec4(color, 1.0);
}
""")

    # Initialize the renderer, using the context manager for safety
    try:
        with OffScreenRenderer(WIDTH, HEIGHT, DUMMY_VERT_PATH, RAYMARCHING_FRAG_PATH) as renderer:
            # Check if initialization was successful inside the context manager
            if renderer.ctx is None:
                print("Skipping rendering due to initialization failure.")
            else:
                # Example: render a single frame at time 0.5
                current_time = 0.5
                start_time = time.time()
                frame_array = renderer.render_frame(current_time)
                end_time = time.time()
                print(f"Rendering time for frame at iTime={current_time}: {end_time - start_time:.4f} seconds.")
                
                if frame_array is not None:
                    print(f"Shape of the rendered frame: {frame_array.shape}")
                    
                    # Convert to 8-bit integer and save
                    # Note: We discard the alpha channel (fourth component) for simple display if it's always 1.0
                    img_data_uint8 = (frame_array[:, :, :3] * 255).astype(np.uint8) 
                    img = Image.fromarray(img_data_uint8, 'RGB')
                    img.save("rendered_sdf_output.png")
                    print("Frame saved as rendered_sdf_output.png")
                    
    except RuntimeError as e:
        print(f"An error occurred during rendering setup or execution: {e}")